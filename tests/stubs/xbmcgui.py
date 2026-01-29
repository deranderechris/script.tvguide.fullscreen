class ListItem:
    def __init__(self, label=''):
        self.label = label

class Window:
    pass

class WindowXML(Window):
    def __init__(self, *args, **kwargs):
        pass

class WindowXMLDialog(Window):
    def __init__(self, *args, **kwargs):
        pass

class Control:
    def __init__(self, *args, **kwargs):
        pass

class ControlImage(Control):
    pass

class ControlLabel(Control):
    pass

class Dialog:
    def ok(self, *args):
        return True
