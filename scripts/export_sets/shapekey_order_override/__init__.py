from . import props, ui_operators, ui_panel


modules = [
    props,
    ui_operators,
    ui_panel,
]


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
