from pathlib import Path
from typing import Optional


class Recipe:
    """
    Класс, описывающий один ресурс (рецепт его добычи).

    Атрибуты:
        name (str): Имя ресурса (например, "wood", "stone")
        template_path (Path): Путь к картинке-образцу (template.png)
        pause (float): Пауза после клика в секундах
        enabled (bool): Включён ли ресурс для автоматического фарма
    """

    def __init__(self, name: str, template_path: Path, pause: float = 2.0, enabled: bool = True):
        self.name = name
        self.template_path = Path(template_path)
        self.pause = pause
        self.enabled = enabled

    def __repr__(self) -> str:
        """Представление объекта для отладки"""
        status = "включён" if self.enabled else "выключен"
        return f"Recipe({self.name}, пауза={self.pause}с, {status})"

    def __str__(self) -> str:
        """Красивый вывод для пользователя"""
        status = "✓" if self.enabled else "✗"
        return f"[{status}] {self.name} (пауза: {self.pause}с)"

    def disable(self):
        """Выключить ресурс"""
        self.enabled = False

    def enable(self):
        """Включить ресурс"""
        self.enabled = True

    def toggle(self):
        """Переключить состояние (вкл/выкл)"""
        self.enabled = not self.enabled

    def to_dict(self) -> dict:
        """Превращает объект в словарь (для сохранения в JSON)"""
        return {
            "name": self.name,
            "template_path": str(self.template_path),
            "pause": self.pause,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Recipe":
        """Создаёт объект из словаря (для загрузки из JSON)"""
        return cls(
            name=data["name"],
            template_path=Path(data["template_path"]),
            pause=data.get("pause", 2.0),
            enabled=data.get("enabled", True)
        )
