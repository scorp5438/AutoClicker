import os
import json
import shutil
from pathlib import Path
from typing import List, Optional

from models.recipe import Recipe
from utils.screenshot import ScreenshotFinder


class RecipeManager:
    """
    Управляет рецептами: загрузка, сохранение, добавление, удаление.

    Структура папок:
        data/recipes/
            wood/
                template.png
                config.json
            stone/
                template.png
                config.json
    """

    def __init__(self, base_path: str = "data/recipes"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.recipes: List[Recipe] = []
        self.finder = ScreenshotFinder()
        self.load_all()

    def load_all(self):
        """Загружает все рецепты из папки data/recipes/"""
        self.recipes = []

        if not self.base_path.exists():
            return

        for recipe_dir in self.base_path.iterdir():
            if not recipe_dir.is_dir():
                continue

            config_file = recipe_dir / "config.json"
            template_file = recipe_dir / "template.png"

            if not config_file.exists() or not template_file.exists():
                print(f"⚠️ Пропускаем {recipe_dir.name}: отсутствует config.json или template.png")
                continue

            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                recipe = Recipe(
                    name=recipe_dir.name,
                    template_path=template_file,
                    pause=data.get("pause", 2.0),
                    enabled=data.get("enabled", True)
                )
                self.recipes.append(recipe)
            except Exception as e:
                print(f"⚠️ Ошибка загрузки {recipe_dir.name}: {e}")

        # Сортируем по имени для удобства
        self.recipes.sort(key=lambda r: r.name)

    def save_recipe(self, recipe: Recipe):
        """Сохраняет рецепт в файл (обновляет config.json)"""
        recipe_dir = self.base_path / recipe.name
        recipe_dir.mkdir(parents=True, exist_ok=True)

        config_file = recipe_dir / "config.json"
        data = {
            "pause": recipe.pause,
            "enabled": recipe.enabled
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def delete_recipe(self, name: str) -> bool:
        """Удаляет папку с рецептом полностью"""
        recipe_dir = self.base_path / name

        if not recipe_dir.exists():
            return False

        shutil.rmtree(recipe_dir)

        # Удаляем из списка
        self.recipes = [r for r in self.recipes if r.name != name]
        return True

    def get_all_recipes(self) -> List[Recipe]:
        """Возвращает список всех рецептов"""
        return self.recipes.copy()

    def get_recipe(self, name: str) -> Optional[Recipe]:
        """Находит рецепт по имени"""
        for recipe in self.recipes:
            if recipe.name == name:
                return recipe
        return None

    def get_enabled_recipes(self) -> List[Recipe]:
        """Возвращает только включённые рецепты"""
        return [r for r in self.recipes if r.enabled]

    # ========== ИНТЕРАКТИВНЫЕ МЕТОДЫ ДЛЯ КОНСОЛИ ==========

    def capture_template(self, recipe_name: str, size: int = 50) -> Optional[Path]:
        """
        Захватывает образец экрана в текущем положении мыши.
        Использует ScreenshotFinder для захвата.

        Args:
            recipe_name: Имя рецепта (для создания папки)
            size: Размер квадратной области захвата

        Returns:
            Path к сохранённому шаблону или None
        """
        if not self.finder.libraries_ok:
            print("❌ Библиотеки не загружены. Установите: pip install opencv-python pyautogui numpy")
            return None

        print("Наведите мышь на объект и нажмите Enter...")
        input()

        # Захватываем область под курсором
        screenshot = self.finder.capture_template_under_mouse(size=size)
        if not screenshot:
            print("❌ Ошибка захвата образца")
            return None

        # Сохраняем
        recipe_dir = self.base_path / recipe_name
        recipe_dir.mkdir(parents=True, exist_ok=True)
        template_path = recipe_dir / "template.png"
        screenshot.save(template_path)

        print(f"✅ Образец сохранён: {template_path}")
        return template_path

    def add_recipe_interactive(self):
        """Интерактивное добавление нового рецепта"""
        print("\n--- ДОБАВЛЕНИЕ НОВОГО РЕСУРСА ---")

        name = input("Введите имя ресурса (например: wood, stone, iron): ").strip().lower()

        if not name:
            print("❌ Имя не может быть пустым")
            return

        # Проверяем на недопустимые символы
        invalid_chars = '<>:"/\\|?*'
        if any(c in name for c in invalid_chars):
            print(f"❌ Имя содержит недопустимые символы: {invalid_chars}")
            return

        if self.get_recipe(name):
            print(f"❌ Ресурс '{name}' уже существует")
            return

        # Захватываем образец
        template_path = self.capture_template(name)
        if not template_path:
            return

        try:
            pause_input = input("Пауза после клика (секунды, например 2.5, Enter = 2.0): ").strip()
            if pause_input:
                pause = float(pause_input)
            else:
                pause = 2.0

            if pause <= 0:
                print("❌ Пауза должна быть больше 0. Использую 2.0")
                pause = 2.0
        except ValueError:
            print("❌ Неверное число. Использую паузу 2.0")
            pause = 2.0

        # Создаём рецепт
        recipe = Recipe(name, template_path, pause, enabled=True)
        self.save_recipe(recipe)
        self.recipes.append(recipe)
        self.recipes.sort(key=lambda r: r.name)

        print(f"✅ Ресурс '{name}' успешно добавлен!")

        # Небольшая подсказка
        print(f"\n💡 Совет: Если скрипт плохо находит '{name}', удалите ресурс и добавьте заново,")
        print("   захватив более чёткий образец (только объект, без лишнего фона).")

    def add_recipe_from_image(self, name: str, image_path: Path, pause: float = 2.0) -> bool:
        """
        Добавляет рецепт из готового изображения (для программистов).

        Args:
            name: Имя ресурса
            image_path: Путь к готовому изображению-шаблону
            pause: Пауза после клика

        Returns:
            True если успешно, иначе False
        """
        if self.get_recipe(name):
            print(f"❌ Ресурс '{name}' уже существует")
            return False

        if not image_path.exists():
            print(f"❌ Изображение не найдено: {image_path}")
            return False

        # Копируем изображение в папку рецепта
        recipe_dir = self.base_path / name
        recipe_dir.mkdir(parents=True, exist_ok=True)

        dest_path = recipe_dir / "template.png"
        shutil.copy2(image_path, dest_path)

        # Создаём рецепт
        recipe = Recipe(name, dest_path, pause, enabled=True)
        self.save_recipe(recipe)
        self.recipes.append(recipe)
        self.recipes.sort(key=lambda r: r.name)

        print(f"✅ Ресурс '{name}' добавлен из изображения")
        return True

    def delete_recipe_interactive(self):
        """Интерактивное удаление рецепта"""
        print("\n--- УДАЛЕНИЕ РЕСУРСА ---")

        if not self.recipes:
            print("❌ Нет добавленных ресурсов")
            return

        print("Доступные ресурсы:")
        for i, recipe in enumerate(self.recipes, 1):
            # Показываем статус для удобства
            status = "✓" if recipe.enabled else "✗"
            print(f"  {i}. {recipe.name} [{status}] пауза: {recipe.pause}с")

        try:
            choice = int(input("Выберите номер для удаления (0 - отмена): "))
            if choice == 0:
                print("❌ Отменено")
                return

            if 1 <= choice <= len(self.recipes):
                recipe = self.recipes[choice - 1]
                confirm = input(f"Удалить '{recipe.name}'? (y/N): ").lower()
                if confirm == 'y' or confirm == 'да':
                    self.delete_recipe(recipe.name)
                    print(f"✅ Ресурс '{recipe.name}' удалён")
                else:
                    print("❌ Отменено")
            else:
                print("❌ Неверный номер")
        except ValueError:
            print("❌ Введите число")

    def toggle_recipe_interactive(self):
        """Интерактивное включение/выключение рецепта"""
        print("\n--- ВКЛЮЧИТЬ/ВЫКЛЮЧИТЬ РЕСУРС ---")

        if not self.recipes:
            print("❌ Нет добавленных ресурсов")
            return

        print("Доступные ресурсы:")
        for i, recipe in enumerate(self.recipes, 1):
            status = "ВКЛ" if recipe.enabled else "ВЫКЛ"
            print(f"  {i}. {recipe.name} [{status}] пауза: {recipe.pause}с")

        try:
            choice = int(input("Выберите номер (0 - отмена): "))
            if choice == 0:
                print("❌ Отменено")
                return

            if 1 <= choice <= len(self.recipes):
                recipe = self.recipes[choice - 1]
                old_status = recipe.enabled
                recipe.toggle()
                self.save_recipe(recipe)
                status = "включён" if recipe.enabled else "выключен"
                print(f"✅ Ресурс '{recipe.name}' был {'ВКЛЮЧЁН' if old_status else 'ВЫКЛЮЧЁН'}, теперь {status}")
            else:
                print("❌ Неверный номер")
        except ValueError:
            print("❌ Введите число")

    def change_pause_interactive(self):
        """Интерактивное изменение паузы"""
        print("\n--- ИЗМЕНЕНИЕ ПАУЗЫ ---")

        if not self.recipes:
            print("❌ Нет добавленных ресурсов")
            return

        print("Доступные ресурсы:")
        for i, recipe in enumerate(self.recipes, 1):
            status = "✓" if recipe.enabled else "✗"
            print(f"  {i}. {recipe.name} [{status}] пауза: {recipe.pause}с")

        try:
            choice = int(input("Выберите номер (0 - отмена): "))
            if choice == 0:
                print("❌ Отменено")
                return

            if 1 <= choice <= len(self.recipes):
                recipe = self.recipes[choice - 1]
                current_pause = recipe.pause

                try:
                    pause_input = input(
                        f"Новая пауза для '{recipe.name}' (текущая {current_pause}с, Enter - без изменений): ").strip()
                    if not pause_input:
                        print("✅ Пауза не изменена")
                        return

                    new_pause = float(pause_input)
                    if new_pause <= 0:
                        print("❌ Пауза должна быть больше 0")
                        return

                    recipe.pause = new_pause
                    self.save_recipe(recipe)
                    print(f"✅ Пауза для '{recipe.name}' изменена с {current_pause}с на {new_pause}с")
                except ValueError:
                    print("❌ Неверное число")
            else:
                print("❌ Неверный номер")
        except ValueError:
            print("❌ Введите число")

    def export_recipe(self, name: str, export_path: Path) -> bool:
        """
        Экспортирует рецепт в zip-архив (для обмена с другими пользователями).

        Args:
            name: Имя рецепта
            export_path: Путь для сохранения архива

        Returns:
            True если успешно
        """
        recipe = self.get_recipe(name)
        if not recipe:
            print(f"❌ Рецепт '{name}' не найден")
            return False

        try:
            import zipfile
            recipe_dir = self.base_path / name

            with zipfile.ZipFile(export_path, 'w') as zipf:
                for file_path in recipe_dir.iterdir():
                    zipf.write(file_path, arcname=file_path.name)

            print(f"✅ Рецепт '{name}' экспортирован в {export_path}")
            return True
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            return False

    def import_recipe(self, archive_path: Path) -> bool:
        """
        Импортирует рецепт из zip-архива.

        Args:
            archive_path: Путь к архиву

        Returns:
            True если успешно
        """
        try:
            import zipfile
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)

                # Распаковываем архив
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    zipf.extractall(tmp_path)

                # Ищем config.json, чтобы узнать имя рецепта
                config_file = tmp_path / "config.json"
                if not config_file.exists():
                    print("❌ Архив не содержит config.json")
                    return False

                with open(config_file, 'r') as f:
                    config = json.load(f)

                # Здесь нет имени рецепта в config, используем имя папки или файла
                # Проще: имя рецепта = имя архива без расширения
                recipe_name = archive_path.stem

                # Проверяем, не существует ли уже
                if self.get_recipe(recipe_name):
                    print(f"❌ Рецепт '{recipe_name}' уже существует")
                    return False

                # Копируем файлы
                recipe_dir = self.base_path / recipe_name
                recipe_dir.mkdir(parents=True, exist_ok=True)

                for file_path in tmp_path.iterdir():
                    shutil.copy2(file_path, recipe_dir / file_path.name)

                # Загружаем рецепт
                self.load_all()
                print(f"✅ Рецепт '{recipe_name}' импортирован")
                return True

        except Exception as e:
            print(f"❌ Ошибка импорта: {e}")
            return False


# Пример использования (для теста)
if __name__ == "__main__":
    """
    Тестирование менеджера рецептов.
    Запустите этот файл отдельно для проверки.
    """
    mgr = RecipeManager()
    print(f"Загружено рецептов: {len(mgr.get_all_recipes())}")
    for r in mgr.get_all_recipes():
        print(f"  - {r}")