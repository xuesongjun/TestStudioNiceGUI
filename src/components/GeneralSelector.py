from typing import List, Callable, Any, Optional
from nicegui import ui

class GeneralSelector:
    """通用选择器组件，支持返回选择并返回列表结果"""
    def __init__(self, 
                 selector_name: str, 
                 options: List[Any],
                 value: Optional[Any] = None,
                 items_per_row: int = 4,
                 items_per_line_in_result: int = 5,
                 on_selection_change: Optional[Callable[[List[Any]], None]] = None):
        self.selector_name = selector_name
        self.options = options
        self.selected_items = set(value) if value is not None else set()
        self.is_expanded = False
        self.items_per_row = items_per_row
        self.items_per_line_in_result = items_per_line_in_result
        self.on_selection_change = on_selection_change
        self.create_ui()
    
    def create_ui(self):
        with ui.card().classes('p-5 w-auto max-w-2xl'):
            self.create_header()
            self.create_content()
        self.selected_container = ui.column().classes('mt-4 text-slate-600')
        self.update_selected_display()
    
    def create_header(self):
        with ui.row().classes('justify-between items-center mb-4'):
            ui.label(self.selector_name).classes('font-bold text-lg')
            self.toggle_btn = ui.button(
                '+', 
                on_click=self.toggle_expansion
            ).classes('w-10 h-10 p-0 bg-blue-500 text-white rounded-full')
    
    def create_content(self):
        self.content = ui.column().classes('hidden space-y-4')
        with self.content:
            with ui.row().classes('gap-4'):
                ui.button('全选', on_click=self.select_all).classes(
                    'px-4 py-2 bg-blue-500 text-white rounded'
                )
                ui.button('全清', on_click=self.deselect_all).classes(
                    'px-4 py-2 bg-blue-500 text-white rounded'
                )
            with ui.grid(columns=self.items_per_row).classes('gap-3'):
                self.checkboxes = []
                for item in self.options:
                    cb = ui.checkbox(
                        str(item), 
                        value= item in self.selected_items,
                        on_change=lambda e, item=item: self.update_selection(item, e.value)
                    )
                    cb.classes('py-1 px-0')
                    self.checkboxes.append(cb)
    
    def toggle_expansion(self):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.content.classes(remove='hidden')
            self.toggle_btn.text = '-'
        else:
            self.content.classes(add='hidden')
            self.toggle_btn.text = '+'
    
    def update_selection(self, item, is_selected):
        if is_selected:
            self.selected_items.add(item)
        else:
            self.selected_items.discard(item)
        self.update_selected_display()
        if self.on_selection_change:
            self.on_selection_change(self.get_selected_list())
    
    def select_all(self):
        self.selected_items = set(self.options)
        for cb in self.checkboxes:
            cb.value = True
        self.update_selected_display()
        if self.on_selection_change:
            self.on_selection_change(self.get_selected_list())
    
    def deselect_all(self):
        self.selected_items.clear()
        for cb in self.checkboxes:
            cb.value = False
        self.update_selected_display()
        if self.on_selection_change:
            self.on_selection_change(self.get_selected_list())
    
    def update_selected_display(self):
        self.selected_container.clear()
        if not self.selected_items:
            with self.selected_container:
                ui.label("暂无选择").classes('text-slate-400 italic')
            return
        with self.selected_container:
            ui.label(f"已选{self.selector_name}:").classes('font-medium text-lg mb-2')
            sorted_list = self.get_selected_list()
            groups = [
                sorted_list[i:i+self.items_per_line_in_result] 
                for i in range(0, len(sorted_list), self.items_per_line_in_result)
            ]
            for group in groups:
                group_text = ", ".join(str(item) for item in group)
                ui.label(group_text).classes('mb-1 text-base')
    
    def get_selected_list(self) -> List[Any]:
        try:
            return sorted(self.selected_items)
        except TypeError:
            return list(self.selected_items)
