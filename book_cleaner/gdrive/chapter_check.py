#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт проверки обозначений глав: ищет слово CHAPTER и проверяет,
что правильный заголовок главы имеет вид ###CHAPTER###.
В отчёт попадают только книги, где найдено слово CHAPTER без обрамления ###.
"""

import re
import argparse
from pathlib import Path

# Правильный заголовок главы: ###CHAPTER###
CORRECT_CHAPTER_PATTERN = re.compile(r'###CHAPTER###')
# Все вхождения слова CHAPTER (как отдельного слова, только заглавными)
ALL_CHAPTER_PATTERN = re.compile(r'\bCHAPTER\b')


def read_text_safely(filepath, encodings_to_try=('utf-8', 'windows-1251', 'cp1252', 'utf-8-sig')):
    """Читает файл в одной из поддерживаемых кодировок."""
    for enc in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    return None


def count_bad_chapters(text):
    """
    Считает вхождения слова CHAPTER, которые НЕ имеют вида ###CHAPTER###.
    На слово 'Chapter' (с маленькой буквы) не реагируем — учитываем только CHAPTER.
    """
    if not text:
        return 0
    correct_count = len(CORRECT_CHAPTER_PATTERN.findall(text))
    all_uppercase_count = len(ALL_CHAPTER_PATTERN.findall(text))
    return max(0, all_uppercase_count - correct_count)


def main():
    parser = argparse.ArgumentParser(
        description="Проверка обозначений глав: CHAPTER должен быть в виде ###CHAPTER###."
    )
    parser.add_argument(
        "books_dir",
        type=str,
        help="Путь до корневой папки с папками книг (в каждой папке — .txt файлы)"
    )
    args = parser.parse_args()

    base_path = Path(args.books_dir)
    if not base_path.exists() or not base_path.is_dir():
        print(f"❌ Ошибка: Папка '{args.books_dir}' не найдена!")
        return

    folders = sorted(
        [d for d in base_path.iterdir() if d.is_dir()],
        key=lambda d: d.name.lower()
    )
    if not folders:
        print(f"❌ В папке нет подпапок.")
        return

    print(f"📁 Найдено папок: {len(folders)}\n", flush=True)

    report_lines = []
    report_lines.append("ОТЧЕТ: неправильные обозначения CHAPTER (без ### ... ###)")
    report_lines.append(f"Папка: {args.books_dir}\n")
    report_lines.append("-" * 70)

    books_with_issues = []  # (относительный путь, количество проблем)
    total_txt_files = 0

    for folder_idx, folder in enumerate(folders, start=1):
        txt_files = list(folder.glob("*.txt"))
        if not txt_files:
            continue
        for txt_file in sorted(txt_files, key=lambda p: p.name.lower()):
            total_txt_files += 1
            rel_path = folder.name + "/" + txt_file.name
            print(f"  [{folder_idx}/{len(folders)}] {rel_path}", flush=True)
            text = read_text_safely(txt_file)
            if text is None:
                report_lines.append(f"[ОШИБКА ЧТЕНИЯ] {rel_path}")
                continue
            bad_count = count_bad_chapters(text)
            if bad_count > 0:
                books_with_issues.append((rel_path, bad_count))

    # В отчёте — только книги с проблемами; напротив каждой — число проблем
    if not books_with_issues:
        report_lines.append("Книг с неправильными обозначениями CHAPTER не найдено.")
    else:
        for rel_path, count in books_with_issues:
            report_lines.append(f"{rel_path} — {count}")

    report_lines.append("-" * 70)
    summary = "\n" + "=" * 50 + "\n"
    summary += "  ИТОГИ\n"
    summary += "=" * 50 + "\n\n"
    summary += f"  Проверено файлов: {total_txt_files}\n"
    summary += f"  Книг с неправильными CHAPTER: {len(books_with_issues)}\n"
    summary += "=" * 50
    report_lines.append(summary)

    report_file = Path("chapter_check_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    print("✅ Проверка завершена!", flush=True)
    print(summary, flush=True)
    print(f"\n📄 Отчет сохранен: {report_file}", flush=True)


if __name__ == "__main__":
    main()
