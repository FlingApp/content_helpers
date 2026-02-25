import os
import re
import argparse
import time
import shutil
from datetime import datetime
from pathlib import Path

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
# Регулярные выражения
HIDDEN_CHARS_RE = re.compile(r'[\u200B\uFEFF\u200E\u200F]')
DOUBLE_SPACES_RE = re.compile(r' {2,}')

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def create_backup(file_path, root_books_dir, backup_root_dir):
    """
    Создает копию файла, сохраняя структуру папок.
    file_path: полный путь к файлу на Гугл Диске
    root_books_dir: путь к корневой папке books (чтобы вычислить относительный путь)
    backup_root_dir: куда складывать бэкапы
    """
    try:
        # Вычисляем относительный путь (например: HarryPotter/text.txt)
        relative_path = file_path.relative_to(root_books_dir)
        # Собираем полный путь для бэкапа
        backup_path = backup_root_dir / relative_path
        
        # Создаем папки, если их нет
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Копируем файл
        shutil.copy2(file_path, backup_path)
        return True, str(backup_path)
    except Exception as e:
        return False, str(e)

def read_text_safely(filepath, max_retries=3):
    """Чтение с защитой от таймаутов и авто-определением кодировки."""
    encodings_to_try = ['utf-8', 'windows-1251', 'cp1252', 'utf-8-sig']
    
    for attempt in range(max_retries):
        for enc in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    return f.read(), enc
            except UnicodeDecodeError:
                continue
            except (TimeoutError, OSError):
                break # Сетевая ошибка, идем на ретрай
        
        # Если цикл кодировок пройден, но ничего не вернули (или был break)
        if attempt < max_retries - 1:
            print(f"⏳ Ожидание чтения файла: {filepath.name} (попытка {attempt + 1})...")
            time.sleep(2)
            
    return None, "Ошибка чтения или неизвестная кодировка"

def write_text_safely(filepath, content, max_retries=3):
    """Запись файла строго в UTF-8 с защитой от блокировки файла облаком."""
    for attempt in range(max_retries):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Success"
        except (TimeoutError, OSError) as e:
            if attempt < max_retries - 1:
                print(f"⏳ Файл занят, ожидание записи: {filepath.name}...")
                time.sleep(2)
            else:
                return False, str(e)
    return False, "Не удалось записать файл после всех попыток"

def clean_text_content(text):
    """
    Основная логика очистки. 
    Возвращает очищенный текст.
    """
    lines = text.split('\n')
    cleaned_lines = []
    empty_line_count = 0

    for line in lines:
        # 1. Удаляем скрытые символы и \r
        line = line.replace('\r', '') # Важно для корректной работы trim
        line = HIDDEN_CHARS_RE.sub('', line)

        # 2. Тримминг
        line = line.strip()

        # 3. Убираем двойные пробелы
        line = DOUBLE_SPACES_RE.sub(' ', line)

        # 4. Логика абзацев (макс 1 пустая строка подряд)
        if line == '':
            empty_line_count += 1
            if empty_line_count > 1:
                continue # Пропускаем лишний перенос
        else:
            empty_line_count = 0

        cleaned_lines.append(line)

    # Собираем обратно через \n
    return '\n'.join(cleaned_lines)

def main():
    parser = argparse.ArgumentParser(description="БОЕВОЙ скрипт очистки книг.")
    parser.add_argument("books_dir", type=str, help="Путь до корневой папки с книгами")
    parser.add_argument("--limit", type=int, default=100, help="Лимит папок (0 - все). Default: 100")
    parser.add_argument("--offset", type=int, default=0, help="Сколько пропустить. Default: 0")
    
    args = parser.parse_args()
    
    base_path = Path(args.books_dir)
    if not base_path.exists():
        print(f"❌ Папка не найдена: {args.books_dir}")
        return

    # Создаем папку для бэкапов в текущей директории
    backup_root = Path(f"./backups_{get_timestamp()}")
    backup_root.mkdir(exist_ok=True)
    print(f"📦 Бэкапы будут сохраняться в: {backup_root.resolve()}")

    all_folders = sorted([d for d in base_path.iterdir() if d.is_dir()])
    
    start_idx = args.offset
    end_idx = len(all_folders) if args.limit == 0 else args.offset + args.limit
    target_folders = all_folders[start_idx:end_idx]
    
    print(f"🚀 ЗАПУСК ОЧИСТКИ: папки [{start_idx} ... {end_idx - 1}] (Всего: {len(target_folders)})")
    
    report_lines = []
    report_lines.append(f"ОТЧЕТ ОЧИСТКИ (CLEAN RUN) - {get_timestamp()}")
    report_lines.append(f"Папка: {args.books_dir}")
    report_lines.append(f"Бэкапы: {backup_root.resolve()}\n")
    report_lines.append("-" * 70)

    stats = {"processed": 0, "changed": 0, "skipped": 0, "errors": 0}

    for folder in target_folders:
        txt_files = list(folder.glob("*.txt"))
        
        if not txt_files:
            continue

        for txt_file in txt_files:
            stats["processed"] += 1
            
            # 1. Читаем
            original_text, encoding = read_text_safely(txt_file)
            if original_text is None:
                stats["errors"] += 1
                report_lines.append(f"[ОШИБКА ЧТЕНИЯ] {folder.name}/{txt_file.name} — {encoding}")
                continue

            # 2. Чистим
            cleaned_text = clean_text_content(original_text)

            # 3. Сравниваем
            if original_text == cleaned_text:
                stats["skipped"] += 1
                # Если файл чист, но был не в utf-8, можно было бы перезаписать, 
                # но пока следуем правилу "не трогай, если текст не меняется визуально".
                # Можно раскомментировать, если важно форсировать UTF-8 даже для чистых файлов:
                # if encoding.lower() not in ['utf-8', 'utf-8-sig']: pass else: continue
                continue

            # 4. Если есть изменения — БЭКАПИМ
            backup_ok, backup_msg = create_backup(txt_file, base_path, backup_root)
            if not backup_ok:
                stats["errors"] += 1
                report_lines.append(f"[ОШИБКА БЭКАПА] {folder.name}/{txt_file.name} — Не удалось создать копию: {backup_msg}")
                continue # Не перезаписываем без бэкапа!

            # 5. Перезаписываем
            write_ok, write_msg = write_text_safely(txt_file, cleaned_text)
            if write_ok:
                stats["changed"] += 1
                report_lines.append(f"[ИСПРАВЛЕН] {folder.name}/{txt_file.name}")
                report_lines.append(f"    - Кодировка: {encoding} -> UTF-8")
                report_lines.append(f"    - Бэкап: {backup_msg}")
            else:
                stats["errors"] += 1
                report_lines.append(f"[ОШИБКА ЗАПИСИ] {folder.name}/{txt_file.name} — {write_msg}")

    # Итоги
    summary = "\n" + "="*30 + "\nИТОГИ РАБОТЫ:\n" + "="*30 + "\n"
    summary += f"Всего обработано файлов: {stats['processed']}\n"
    summary += f"✅ Исправлено и сохранено: {stats['changed']}\n"
    summary += f"💤 Пропущено (не требовали правок): {stats['skipped']}\n"
    summary += f"❌ Ошибки (см. лог): {stats['errors']}\n"
    summary += f"📂 Папка с бэкапами: {backup_root}"

    report_lines.append(summary)
    
    report_file = f"clean_report_{get_timestamp()}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    print(summary)
    print(f"📝 Подробный отчет сохранен в: {report_file}")

if __name__ == "__main__":
    main()