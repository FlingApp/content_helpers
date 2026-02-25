import os
import re
import argparse
import time
from pathlib import Path

# Регулярные выражения для поиска проблем
HIDDEN_CHARS_RE = re.compile(r'[\u200B\uFEFF\u200E\u200F]')
DOUBLE_SPACES_RE = re.compile(r' {2,}')

def read_text_safely(filepath, max_retries=3):
    """
    Попытка прочитать файл в разных кодировках с защитой от сетевых таймаутов Google Drive.
    """
    encodings_to_try =['utf-8', 'windows-1251', 'cp1252', 'utf-8-sig']
    last_error = ""

    for attempt in range(max_retries):
        for enc in encodings_to_try:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    return f.read(), enc
            except UnicodeDecodeError:
                continue  # Кодировка не подошла, пробуем следующую
            except (TimeoutError, OSError) as e:
                # Поймали ошибку диска/сети (например, таймаут от Гугл Диска)
                last_error = str(e)
                break # Прерываем цикл кодировок и идем на повторную попытку (retry)

        else:
            # Если цикл кодировок закончился без break, значит ни одна кодировка не подошла
            return None, "Неизвестная кодировка"
        
        # Если мы тут, значит сработал break из-за таймаута скачивания
        print(f"⏳ Ожидание файла из облака: {filepath.name} (попытка {attempt + 1}/{max_retries})...")
        time.sleep(2) # Ждем n секунд, чтобы Google Drive успел докачать файл
        
    # Если все попытки исчерпаны
    return None, f"Ошибка доступа к файлу (таймаут облака): {last_error}"

def analyze_text(text):
    """Анализирует текст и возвращает количество найденных проблем."""
    stats = {
        "hidden_chars": 0,
        "edge_spaces": 0,
        "double_spaces": 0,
        "extra_newlines": 0
    }
    
    lines = text.split('\n')
    empty_line_count = 0

    for line in lines:
        if HIDDEN_CHARS_RE.search(line):
            stats["hidden_chars"] += 1
            
        clean_line = line.replace('\r', '').strip()
        if line.replace('\r', '') != clean_line:
            stats["edge_spaces"] += 1
            
        if DOUBLE_SPACES_RE.search(clean_line):
            stats["double_spaces"] += 1
            
        if clean_line == '':
            empty_line_count += 1
            if empty_line_count > 1:
                stats["extra_newlines"] += 1
        else:
            empty_line_count = 0

    return stats

def main():
    parser = argparse.ArgumentParser(description="Холостой прогон (Dry Run) для проверки файлов.")
    parser.add_argument("books_dir", type=str, help="Путь до корневой папки с книгами")
    parser.add_argument("--limit", type=int, default=5, help="Сколько папок обрабатывать (0 - все). По умолчанию: 10")
    parser.add_argument("--offset", type=int, default=0, help="Сколько папок пропустить. По умолчанию: 0")
    
    args = parser.parse_args()
    
    base_path = Path(args.books_dir)
    if not base_path.exists() or not base_path.is_dir():
        print(f"❌ Ошибка: Папка '{args.books_dir}' не найдена!")
        return

    all_folders = sorted([d for d in base_path.iterdir() if d.is_dir()])
    total_folders = len(all_folders)
    
    print(f"📁 Всего найдено папок: {total_folders}")

    start_idx = args.offset
    end_idx = total_folders if args.limit == 0 else args.offset + args.limit
    target_folders = all_folders[start_idx:end_idx]
    
    print(f"🚀 Запуск: индексы[{start_idx} ... {end_idx - 1}] (Всего к проверке: {len(target_folders)})\n")
    
    report_lines =[]
    report_lines.append(f"ОТЧЕТ ХОЛОСТОГО ПРОГОНА (DRY RUN)")
    report_lines.append(f"Папка: {args.books_dir} | Offset: {args.offset} | Limit: {args.limit if args.limit != 0 else 'Все'}\n")
    report_lines.append("-" * 70)

    total_txt_files = 0
    files_with_issues = 0
    errors = 0

    for folder in target_folders:
        txt_files = list(folder.glob("*.txt"))
        
        if not txt_files:
            report_lines.append(f"[ПРОПУСК] {folder.name}/ — нет .txt файлов")
            continue

        for txt_file in txt_files:
            total_txt_files += 1
            text, result_info = read_text_safely(txt_file)
            
            if text is None:
                # Если файл так и не прочитался, логируем это и не роняем скрипт
                errors += 1
                report_lines.append(f"[ОШИБКА] {folder.name}/{txt_file.name} — {result_info}")
                continue
                
            stats = analyze_text(text)
            
            total_issues = sum(stats.values())
            if total_issues > 0:
                files_with_issues += 1
                report_lines.append(f"[НАЙДЕНЫ ПРОБЛЕМЫ] {folder.name}/{txt_file.name} (Кодировка: {result_info})")
                if stats['hidden_chars'] > 0: report_lines.append(f"    - Скрытых символов: {stats['hidden_chars']} строк")
                if stats['edge_spaces'] > 0: report_lines.append(f"    - Пробелов по краям: {stats['edge_spaces']} строк")
                if stats['double_spaces'] > 0: report_lines.append(f"    - Двойных пробелов: {stats['double_spaces']} строк")
                if stats['extra_newlines'] > 0: report_lines.append(f"    - Лишних переносов: {stats['extra_newlines']} шт")
            else:
                report_lines.append(f"[ОК] {folder.name}/{txt_file.name} — идеальный файл (Кодировка: {result_info})")
                
        report_lines.append("-" * 70)

    summary = f"\nИТОГИ ПРОГОНА:\n"
    summary += f"Проверено папок: {len(target_folders)}\n"
    summary += f"Найдено .txt файлов: {total_txt_files}\n"
    summary += f"Файлов с ошибками чтения: {errors}\n"
    summary += f"Файлов, требующих очистки: {files_with_issues}"
    
    report_lines.append(summary)
    
    report_file = "dry_run_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    print(f"\n✅ Проверка завершена! Отчет сохранен: {report_file}")
    print(summary)

if __name__ == "__main__":
    main()