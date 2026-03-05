"""
Intelleo PDF Splitter — Animazioni e Transizioni (PySide6)
Collezione di utility per rendere l'interfaccia fluida e moderna.
"""

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class UIAnimations:
    """Utility per l'applicazione di animazioni ai widget."""

    @staticmethod
    def fade_in(widget: QWidget, duration: int = 400) -> None:
        """Applica un effetto di fade-in a un widget e lo pulisce al termine."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Pulizia dell'effetto al termine per ripristinare il rendering nativo
        # Questo risolve il problema della GUI nera su alcuni sistemi Windows
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))  # type: ignore
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    @staticmethod
    def slide_fade_transition(old_widget: QWidget, new_widget: QWidget, direction: str = "right") -> None:
        """Esegue una transizione fluida tra due widget (es. cambio tab)."""
        # Fade-out vecchio widget
        old_effect = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(old_effect)

        # Fade-in e slide nuovo widget
        new_effect = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(new_effect)

        group = QParallelAnimationGroup(new_widget)

        # Animazione Opacità
        fade_anim = QPropertyAnimation(new_effect, b"opacity")
        fade_anim.setDuration(300)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Animazione Posizione (Slight slide)
        slide_anim = QPropertyAnimation(new_widget, b"pos")
        slide_anim.setDuration(350)

        offset = 25 if direction == "right" else -25
        start_pos = new_widget.pos() + QPoint(offset, 0)
        end_pos = new_widget.pos()

        slide_anim.setStartValue(start_pos)
        slide_anim.setEndValue(end_pos)
        slide_anim.setEasingCurve(QEasingCurve.Type.OutBack)

        group.addAnimation(fade_anim)
        group.addAnimation(slide_anim)

        # Pulizia effetti al termine
        def cleanup():
            new_widget.setGraphicsEffect(None)  # type: ignore
            old_widget.setGraphicsEffect(None)  # type: ignore

        group.finished.connect(cleanup)

        new_widget.show()
        group.start(QParallelAnimationGroup.DeletionPolicy.DeleteWhenStopped)

    @staticmethod
    def animate_visibility(widget: QWidget, visible: bool, duration: int = 300) -> None:
        """Mostra o nasconde un widget con un effetto di opacità e pulizia."""
        if visible:
            widget.show()
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

            fade = QPropertyAnimation(effect, b"opacity")
            fade.setDuration(duration)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.setEasingCurve(QEasingCurve.Type.OutCubic)

            fade.finished.connect(lambda: widget.setGraphicsEffect(None))  # type: ignore
            fade.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        else:
            widget.hide()

    @staticmethod
    def pulse(widget: QWidget, duration: int = 1000) -> None:
        """Applica un effetto di pulsazione (opacità) al widget."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0.6)
        anim.setEndValue(1.0)
        anim.setLoopCount(-1)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
