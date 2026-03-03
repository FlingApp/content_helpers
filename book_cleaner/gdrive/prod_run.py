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
    last_error = ""

    for attempt in range(max_retries):
        for enc in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    return f.read(), enc
            except UnicodeDecodeError:
                continue
            except (TimeoutError, OSError) as e:
                last_error = str(e)
                break  # Сетевая ошибка, идем на ретрай

        else:
            # Цикл кодировок закончился без break — ни одна не подошла
            return None, "Неизвестная кодировка"

        if attempt < max_retries - 1:
            print(f"⏳ Ожидание чтения файла: {filepath.name} (попытка {attempt + 1}/{max_retries})...")
            time.sleep(2)

    return None, f"Ошибка доступа к файлу (таймаут облака): {last_error}"

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
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Схлопываем серии из 3+ переносов в 2 (одна пустая строка) — так лишние пустые строки убираются до разбора
    text = re.sub(r'\n{3,}', '\n\n', text)
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

        # 4. Строки только из пробелов считаем пустыми (на случай нестандартных пробельных символов)
        if not line or line.strip() == '':
            line = ''

        # 5. Логика абзацев: макс. 1 пустая строка подряд
        if line == '':
            empty_line_count += 1
            if empty_line_count > 1:
                continue  # Пропускаем лишний перенос
        else:
            empty_line_count = 0

        cleaned_lines.append(line)

    # Собираем обратно через \n
    return '\n'.join(cleaned_lines)

def main():
    parser = argparse.ArgumentParser(description="БОЕВОЙ скрипт очистки книг.")
    parser.add_argument("books_dir", type=str, help="Путь до корневой папки с книгами")
    parser.add_argument("--limit", type=int, default=10, help="Лимит папок (0 - все). По умолчанию: 10")
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

    all_folders = sorted(
        [d for d in base_path.iterdir() if d.is_dir()],
        key=lambda d: d.name.lower()
    )
    
    start_idx = args.offset
    end_idx = len(all_folders) if args.limit == 0 else args.offset + args.limit
    target_folders = all_folders[start_idx:end_idx]
    
    print(f"🚀 ЗАПУСК ОЧИСТКИ: папки [{start_idx} ... {end_idx - 1}] (Всего: {len(target_folders)})")
    
    report_lines = []
    report_lines.append(f"ОТЧЕТ ОЧИСТКИ (CLEAN RUN) - {get_timestamp()}")
    report_lines.append(f"Папка: {args.books_dir} | Offset: {args.offset} | Limit: {args.limit if args.limit != 0 else 'Все'}")
    report_lines.append(f"Бэкапы: {backup_root.resolve()}\n")
    report_lines.append("-" * 70)

    stats = {"processed": 0, "changed": 0, "skipped": 0, "errors": 0}

    for folder in target_folders:
        txt_files = list(folder.glob("*.txt"))

        if not txt_files:
            report_lines.append(f"[ПРОПУСК] {folder.name}/ — нет .txt файлов")
            report_lines.append("-" * 70)
            continue

        folder_has_report_line = False
        for txt_file in txt_files:
            stats["processed"] += 1
            
            # 1. Читаем
            original_text, encoding = read_text_safely(txt_file)
            if original_text is None:
                stats["errors"] += 1
                report_lines.append(f"[ОШИБКА] {folder.name}/{txt_file.name} — {encoding}")
                folder_has_report_line = True
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
                folder_has_report_line = True
                continue # Не перезаписываем без бэкапа!

            # 5. Перезаписываем
            write_ok, write_msg = write_text_safely(txt_file, cleaned_text)
            if write_ok:
                stats["changed"] += 1
                report_lines.append(f"[ИСПРАВЛЕН] {folder.name}/{txt_file.name}")
                report_lines.append(f"    - Кодировка: {encoding} -> UTF-8")
                report_lines.append(f"    - Бэкап: {backup_msg}")
                folder_has_report_line = True
            else:
                stats["errors"] += 1
                report_lines.append(f"[ОШИБКА ЗАПИСИ] {folder.name}/{txt_file.name} — {write_msg}")
                folder_has_report_line = True

        if not folder_has_report_line:
            n = len(txt_files)
            report_lines.append(f"[БЕЗ ИЗМЕНЕНИЙ] {folder.name}/ — {n} файл(ов), правки не требовались")

        report_lines.append("-" * 70)

    # Итоги (формат как в dry_run)
    summary = "\n" + "=" * 50 + "\n"
    summary += "  ИТОГИ ОЧИСТКИ (CLEAN RUN)\n"
    summary += "=" * 50 + "\n\n"
    summary += f"  Папок обработано: {len(target_folders)}\n"
    summary += f"  Файлов (.txt): {stats['processed']}\n\n"
    summary += "  —— По файлам ——\n"
    summary += f"  Исправлено и сохранено: {stats['changed']}\n"
    summary += f"  Пропущено (без правок): {stats['skipped']}\n"
    summary += f"  Ошибки (чтение/бэкап/запись): {stats['errors']}\n"
    summary += f"\n  Папка с бэкапами: {backup_root}\n"
    summary += "=" * 50

    report_lines.append(summary)
    
    report_file = f"clean_report_{get_timestamp()}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    print(summary)
    print(f"📝 Подробный отчет сохранен в: {report_file}")

if __name__ == "__main__":
    main()