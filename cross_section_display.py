from PyQt4 import QtGui, QtCore
from vispy import scene
from vispy.scene.visuals import Mesh, Line, Markers
from color_transformations import lab2rgb, lab2rgba
from cross_section import CrossSectionL
import numpy as np


class SliderWithLabel(QtGui.QWidget):
    def __init__(self, label="", *args, **kwargs):
        QtGui.QWidget.__init__(self, *args, **kwargs)
        self.slider = QtGui.QSlider()
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.setRange(1, 99)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.label = QtGui.QLabel(self)
        self.label.setText(label)
        layout = QtGui.QHBoxLayout()
        layout.setMargin(0)
        layout.setSpacing(2)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        self.setLayout(layout)


class CrossSectionDisplay2D(object):
    def __init__(self, cross_section, color_label_prefix=""):
        self.canvas = scene.SceneCanvas(keys='interactive', bgcolor='white')
        self.view = self.canvas.central_widget.add_view()
        self.view.camera.rect = (-110, -140), (230, 230)

        self.color_label_prefix = color_label_prefix
        self.selected_color = None

        self.color_value_label = QtGui.QLabel()
        self.splitter_v = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter_v.addWidget(self.canvas.native)
        self.splitter_v.addWidget(self.color_value_label)

        self.cross_section = cross_section
        self.cs_mesh = Mesh()
        self.view.add(self.cs_mesh)
        self.redraw()

    def add_to_widget(self, parent_widget):
        self.parent_widget = parent_widget
        self.parent_widget.addWidget(self.splitter_v)

    def redraw(self):
        self.cs_mesh.set_data(vertices=self.cross_section.vertices_2d,
                              faces=self.cross_section.faces,
                              vertex_colors=self.cross_section.vertex_colors)
        self.update_color_value_label()

    def set_L(self, L):
        self.cross_section.L = L

    def update_color_value_label(self):
        if self.selected_color is None:
            label_text = ""
        else:
            val_lab = self.selected_color
            val_rgb = lab2rgb(self.selected_color)
            label_text = "L,a,b = {}  R,G,B = {}".format(
                "({:.0f}, {:.0f}, {:.0f})".format(val_lab[0], val_lab[1], val_lab[2]),
                "({:.1f}, {:.1f}, {:.1f})".format(val_rgb[0], val_rgb[1], val_rgb[2]))

        self.color_value_label.setText(
            "{}{}".format(self.color_label_prefix, label_text))


class CrossSectionDisplay2DConstL(CrossSectionDisplay2D):
    def __init__(self, L, color_label_prefix=""):
        cs = CrossSectionL(L)
        super(CrossSectionDisplay2DConstL, self).__init__(cs, color_label_prefix)
        self.sliderlabel = SliderWithLabel()
        self.splitter_v.addWidget(self.sliderlabel)
        self.sliderlabel.slider.valueChanged.connect(self.set_L)

    def add_to_widget(self, parent_widget):
        self.parent_widget = parent_widget
        self.parent_widget.addWidget(self.splitter_v)

    def set_L(self, L):
        self.cross_section.L = L
        self.sliderlabel.slider.setValue(L)
        self.sliderlabel.label.setText("L={}".format(L))
        self.redraw()

class ColoredLine3D(object):
    def __init__(self, parent):
        self.parent = parent
        self.line = Line()
        self.markers = Markers()
        self.markers.set_style('o')
        self.parent.add(self.line)
        self.parent.add(self.markers)

    def update(self, col1, col2, N_markers=5):
        assert (col1 != None and col2 != None)

        col1 = np.asarray(col1, dtype=float)
        col2 = np.asarray(col2, dtype=float)

        pos = np.array([(1-t)*col1 + t*col2 for t in np.linspace(0., 1., 100, endpoint=True)])
        colors = np.array([lab2rgba(pt, clip=True) for pt in pos])
        self.line.set_data(pos=pos, color=colors, width=3)
        self.line.update()

        pos_markers = np.array([(1-t)*col1 + t*col2 for t in np.linspace(0., 1., N_markers, endpoint=True)])
        colors_markers = np.array([lab2rgba(pt, clip=True) for pt in pos_markers])
        self.markers.set_data(pos_markers, face_color=colors_markers)


class CrossSectionDisplay3D(object):
    def __init__(self):
        self.cs_meshes = {}
        self.start_color = None
        self.end_color = None
        self.canvas = scene.SceneCanvas(keys='interactive', bgcolor='white')
        self.view = self.canvas.central_widget.add_view()
        self.view.border_color = (0.5, 0.5, 0.5, 1)
        self.view.camera.rect = (-5, -5), (10, 10)
        self.view.border = (1, 0, 0, 1)
        self.view.set_camera('turntable', mode='perspective', up='z',
                             azimuth=140., elevation=30.,  distance=500)
        self.colored_line = None
        self.redraw()

    def add_to_widget(self, parent_widget):
        self.parent_widget = parent_widget
        self.parent_widget.addWidget(self.canvas.native)

    def add_cross_section(self, cs):
        vertex_colors = cs.vertex_colors
        vertex_colors[:, 3] = 0.7  # smaller alpha value for slight transparency
        mesh = Mesh(vertices=cs.vertices_3d, faces=cs.faces, vertex_colors=vertex_colors)
        self.view.add(mesh)
        self.cs_meshes[cs] = mesh

    def redraw(self):
        self.draw_boxed_coordinate_axes()

        for cs, mesh in self.cs_meshes.iteritems():
            vertex_colors = cs.vertex_colors
            vertex_colors[:, 3] = 0.7  # smaller alpha value for slight transparency
            mesh.set_data(vertices=cs.vertices_3d, faces=cs.faces, vertex_colors=vertex_colors)

        self.draw_colored_line()

    def draw_colored_line(self, N_markers=5):
        """
        Draw a colored line connecting the start and end color. The argument `N`
        specifies how many intermediate colored points to draw.
        """
        if self.start_color is None or self.end_color is None:
            return

        if self.colored_line is None:
            self.colored_line = ColoredLine3D(self.view)

        self.colored_line.update(self.start_color, self.end_color)

    def draw_boxed_coordinate_axes(self):
        Lmin, Lmax = 0, 100
        amin, amax = -110, 120
        bmin, bmax = -140, 90

        box_x = np.array([[Lmin, amin, bmin], [Lmax, amin, bmin],
                          [Lmin, amax, bmin], [Lmax, amax, bmin],
                          [Lmin, amax, bmax], [Lmax, amax, bmax],
                          [Lmin, amin, bmax], [Lmax, amin, bmax]])

        box_y = np.array([[Lmin, amin, bmin], [Lmin, amax, bmin],
                          [Lmax, amin, bmin], [Lmax, amax, bmin],
                          [Lmax, amin, bmax], [Lmax, amax, bmax],
                          [Lmin, amin, bmax], [Lmin, amax, bmax]])

        box_z = np.array([[Lmin, amin, bmin], [Lmin, amin, bmax],
                          [Lmin, amax, bmin], [Lmin, amax, bmax],
                          [Lmax, amax, bmin], [Lmax, amax, bmax],
                          [Lmax, amin, bmin], [Lmax, amin, bmax]])

        self.view.add(Line(pos=box_x, color='red', connect='segments', width=1))
        self.view.add(Line(pos=box_y, color='green', connect='segments', width=1))
        self.view.add(Line(pos=box_z, color='blue', connect='segments', width=1))
