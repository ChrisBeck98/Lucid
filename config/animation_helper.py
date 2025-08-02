from PyQt5.QtCore import QPropertyAnimation, QPoint

def animate_widget(widget, start_pos: QPoint, end_pos: QPoint, duration=200, on_finished=None):
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(start_pos)
    animation.setEndValue(end_pos)

    if on_finished:
        animation.finished.connect(on_finished)

    animation.start()
    # Prevent garbage collection
    widget._animation = animation
