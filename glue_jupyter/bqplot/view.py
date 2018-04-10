import bqplot
import ipywidgets as widgets
from IPython.display import display

from glue.core.roi import RectangularROI, RangeROI
from glue.core.command import ApplySubsetState

from .. import IPyWidgetView

class BqplotBaseView(IPyWidgetView):

    allow_duplicate_data = False
    allow_duplicate_subset = False
    # _state_cls = ImageViewerState
    # _data_artist_cls = BqplotImageLayerArtist
    # _subset_artist_cls = BqplotImageLayerArtist

    def __init__(self, session):
        super(BqplotBaseView, self).__init__(session)
        # session.hub.subscribe(self, SubsetCreateMessage,
        #                       handler=self.receive_message)
        self.state = self._state_cls()

        self.scale_x = bqplot.LinearScale(min=0, max=1)
        self.scale_y = bqplot.LinearScale(min=0, max=1)
        self.scales = {'x': self.scale_x, 'y': self.scale_y}
        self.axis_x = bqplot.Axis(
            scale=self.scale_x, grid_lines='solid', label='x')
        self.axis_y = bqplot.Axis(scale=self.scale_y, orientation='vertical', tick_format='0.2f',
                                  grid_lines='solid', label='y')
        def update_axes(*ignore):
            self.axis_x.label = str(self.state.x_att)
            self.axis_y.label = str(self.state.y_att)
        self.state.add_callback('x_att', update_axes)
        self.state.add_callback('y_att', update_axes)
        self.figure = bqplot.Figure(scales=self.scales, axes=[
                                    self.axis_x, self.axis_y])
        self.figure.padding_y = 0
        
        actions = ['move', 'brush', 'brush x', 'brush y']
        self.interact_map = {}
        self.panzoom = bqplot.PanZoom(scales={'x': [self.scale_x], 'y': [self.scale_y]})
        self.interact_map['move'] = self.panzoom

        self.brush = bqplot.interacts.BrushSelector(x_scale=self.scale_x, y_scale=self.scale_y, color="green")
        self.interact_map['brush'] = self.brush
        self.brush.observe(self.update_brush, "brushing")

        self.brush_x = bqplot.interacts.BrushIntervalSelector(scale=self.scale_x, color="green" )
        self.interact_map['brush x'] = self.brush_x
        self.brush_x.observe(self.update_brush_x, "brushing")

        self.brush_y = bqplot.interacts.BrushIntervalSelector(scale=self.scale_y, color="green", orientation='vertical')
        self.interact_map['brush y'] = self.brush_y
        self.brush_y.observe(self.update_brush_y, "brushing")


        self.button_action = widgets.ToggleButtons(description='Mode: ', options=[(action, action) for action in actions],
                                                   icons=["arrows", "pencil-square-o"])
        self.button_action.observe(self.change_action, "value")
        self.change_action()  # 'fire' manually for intial value

#         self.state.add_callback('y_att', self._update_axes)
#         self.state.add_callback('x_log', self._update_axes)
#         self.state.add_callback('y_log', self._update_axes)

        self.state.add_callback('x_min', self.limits_to_scales)
        self.state.add_callback('x_max', self.limits_to_scales)
        self.state.add_callback('y_min', self.limits_to_scales)
        self.state.add_callback('y_max', self.limits_to_scales)

        self.create_tab()
        self.output_widget = widgets.Output()
        self.main_widget = widgets.VBox(
            children=[self.tab, self.figure, self.output_widget])

    def show(self):
        display(self.main_widget)

    def create_tab(self):
        self.widget_show_axes = widgets.Checkbox(value=False, description="Show axes")
        self.widgets_axis = []
        self.tab_general = widgets.VBox([self.button_action, self.widget_show_axes] + self.widgets_axis)#, self.widget_y_axis, self.widget_z_axis])
        children = [self.tab_general]
        self.tab = widgets.Tab(children)
        self.tab.set_title(0, "General")
        self.tab.set_title(1, "Axes")



    @staticmethod
    def update_viewer_state(rec, context):
        print('update viewer state', rec, context)

    def change_action(self, *ignore):
        self.figure.interaction = self.interact_map[self.button_action.value]
        self.brush.selected = []
        self.brush_x.selected = []

    def update_brush(self, *ignore):
        if not self.brush.brushing:  # only select when we ended
            (x1, y1), (x2, y2) = self.brush.selected
            x = [x1, x2]
            y = [y1, y2]
            roi = RectangularROI(xmin=min(x), xmax=max(x), ymin=min(y), ymax=max(y))
            self.apply_roi(roi)

    def update_brush_x(self, *ignore):
        if not self.brush_x.brushing:  # only select when we ended
            x = self.brush_x.selected
            if x is not None and len(x):
                roi = RangeROI(min=min(x), max=max(x), orientation='x')
                self.apply_roi(roi)

    def update_brush_y(self, *ignore):
        if not self.brush_y.brushing:  # only select when we ended
            y = self.brush_y.selected
            if y is not None and len(y):
                roi = RangeROI(min=min(y), max=max(y), orientation='y')
                self.apply_roi(roi)

    def apply_roi(self, roi):
        # TODO: partial copy paste from glue/viewers/matplotlib/qt/data_viewer.py
        if len(self.layers) > 0:
            subset_state = self._roi_to_subset_state(roi)
            cmd = ApplySubsetState(data_collection=self._data,
                                   subset_state=subset_state)
            self._session.command_stack.do(cmd)
        # else:
        #     # Make sure we force a redraw to get rid of the ROI
        #    self.axes.figure.canvas.draw()

    def apply_roi(self, roi):
        if len(self.layers) > 0:
            subset_state = self._roi_to_subset_state(roi)
            cmd = ApplySubsetState(data_collection=self._data,
                                   subset_state=subset_state)
            self._session.command_stack.do(cmd)
        else:
            # Make sure we force a redraw to get rid of the ROI
            self.axes.figure.canvas.draw()

    def _roi_to_subset_state(self, roi):
        # TODO: copy paste from glue/viewers/image/qt/data_viewer.py#L66

        # next lines don't work.. comp has no datetime?
        #x_date = any(comp.datetime for comp in self.state._get_x_components())
        #y_date = any(comp.datetime for comp in self.state._get_y_components())

        #if x_date or y_date:
        #    roi = roi.transformed(xfunc=mpl_to_datetime64 if x_date else None,
        #                          yfunc=mpl_to_datetime64 if y_date else None)

        x_comp = self.state.x_att.parent.get_component(self.state.x_att)
        y_comp = self.state.y_att.parent.get_component(self.state.y_att)

        return x_comp.subset_from_roi(self.state.x_att, roi,
                                      other_comp=y_comp,
                                      other_att=self.state.y_att,
                                      coord='x')

    def limits_to_scales(self, *args):
        if self.state.x_min is not None and self.state.x_max is not None:
            self.scale_x.min = float(self.state.x_min)
            self.scale_x.max = float(self.state.x_max)

        if self.state.y_min is not None and self.state.y_max is not None:
            self.scale_y.min = float(self.state.y_min)
            self.scale_y.max = float(self.state.y_max)

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = BqplotScatterLayerArtist
        else:
            cls = BqplotImageLayerArtist
        layer = self.get_layer_artist(cls, layer=layer, layer_state=layer_state)
        self._add_layer_tab(layer)
        return layer

    def get_subset_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = BqplotScatterLayerArtist
        else:
            cls = BqplotImageLayerArtist
        layer = self.get_layer_artist(cls, layer=layer, layer_state=layer_state)
        self._add_layer_tab(layer)
        return layer

    def receive_message(self, message):
        print("Message received:")
        print("{0}".format(message))
        self.last_msg = message

    def redraw(self):
        pass # print('redraw view', self.state.x_att, self.state.y_att)

    def redraw(self):
        pass



from glue.viewers.common.qt.data_viewer_with_state import DataViewerWithState
BqplotBaseView.add_data = DataViewerWithState.add_data
BqplotBaseView.add_subset = DataViewerWithState.add_subset

from glue.viewers.image.state import ImageViewerState
from glue.viewers.scatter.state import ScatterViewerState
from glue.viewers.image.composite_array import CompositeArray

from .image import BqplotImageLayerArtist
from .scatter import BqplotScatterLayerArtist
from ..utils import rgba_to_png_data
import numpy as np

class BqplotImageView(BqplotBaseView):
    allow_duplicate_data = False
    allow_duplicate_subset = False
    _state_cls = ImageViewerState

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = BqplotScatterLayerArtist
        else:
            cls = BqplotImageLayerArtist
        layer = self.get_layer_artist(cls, layer=layer, layer_state=layer_state)
        self._add_layer_tab(layer)
        return layer

    def get_subset_layer_artist(self, layer=None, layer_state=None):
        if layer.ndim == 1:
            cls = BqplotScatterLayerArtist
        else:
            cls = BqplotImageLayerArtist
        layer = self.get_layer_artist(cls, layer=layer, layer_state=layer_state)
        self._add_layer_tab(layer)
        return layer


class BqplotScatterView(BqplotBaseView):

    allow_duplicate_data = False
    allow_duplicate_subset = False
    _state_cls = ScatterViewerState
    _data_artist_cls = BqplotScatterLayerArtist
    _subset_artist_cls = BqplotScatterLayerArtist