/**
 * Хранилище ссылок на выбранные аудиофайлы (object URLs).
 * Обновляется из audio_check/index.html при изменении выбора.
 * После запуска indexing.sh также доступны GDRIVE_ITEM_IDS и GDRIVE_ITEM_IDS_BY_BASENAME.
 */
(function () {
    'use strict';
    window.selectedAudioLinks = [];

    /**
     * Возвращает Google Drive item-id по имени файла (из индекса drive_files_list.js).
     * @param {string} filename - имя файла (например "18.mp3")
     * @returns {string|undefined} один id, если файл один; иначе undefined (несколько — смотри getDriveIdsByFilename)
     * @returns {Array<{path: string, id: string}>|undefined} если несколько файлов с таким именем — см. getDriveIdsByFilename
     */
    window.getDriveIdByFilename = function (filename) {
        var byName = window.GDRIVE_ITEM_IDS_BY_BASENAME;
        if (!byName || !filename) return undefined;
        var list = byName[filename];
        if (!list || list.length === 0) return undefined;
        if (list.length === 1) return list[0].id;
        return undefined;
    };

    /**
     * Возвращает все пары { path, id } для данного имени файла.
     * @param {string} filename - имя файла
     * @returns {Array<{path: string, id: string}>}
     */
    window.getDriveIdsByFilename = function (filename) {
        var byName = window.GDRIVE_ITEM_IDS_BY_BASENAME;
        if (!byName || !filename) return [];
        return byName[filename] || [];
    };

    /**
     * Вызов Gemini API (generateContent, без stream).
     * @param {Object} opts
     * @param {string} opts.modelId - ID модели (например "gemini-2.5-pro")
     * @param {string} opts.apiKey - GEMINI_API_KEY
     * @param {string} opts.prompt - текст промпта (первый элемент в contents.parts)
     * @param {Array} [opts.extraParts] - дополнительные parts (например inlineData для аудио — пока не используем)
     * @returns {Promise<{ text: string, error?: string }>}
     */
    window.callGemini = function (opts) {
        var modelId = opts.modelId;
        var apiKey = opts.apiKey;
        var prompt = opts.prompt;
        var extraParts = opts.extraParts || [];

        var parts = [{ text: prompt }].concat(extraParts);
        var body = {
            contents: [
                {
                    role: 'user',
                    parts: parts
                }
            ],
            generationConfig: {
                thinkingConfig: {
                    thinkingBudget: -1
                }
            }
        };

        var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + encodeURIComponent(modelId) + ':generateContent?key=' + encodeURIComponent(apiKey);

        var controller = new AbortController();
        var timeoutId = setTimeout(function () { controller.abort(); }, 120000); // 2 минуты для аудио

        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: controller.signal
        })
            .then(function (res) {
                clearTimeout(timeoutId);
                if (!res.ok) {
                    return res.json().then(function (err) {
                        var msg = (err.error && err.error.message) ? err.error.message : (res.status + ' ' + res.statusText);
                        if (err.error && err.error.code) msg = '[' + err.error.code + '] ' + msg;
                        return { error: msg };
                    }).catch(function () {
                        return { error: res.status + ' ' + res.statusText };
                    });
                }
                return res.json();
            })
            .then(function (data) {
                if (data.error) return data;
                var text = '';
                if (data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts) {
                    data.candidates[0].content.parts.forEach(function (p) {
                        if (p.text) text += p.text;
                    });
                }
                return { text: text };
            })
            .catch(function (err) {
                clearTimeout(timeoutId);
                var msg = err && err.message ? err.message : String(err);
                if (msg === 'Failed to fetch' || err instanceof TypeError) {
                    msg = 'Нет связи с сервером. Откройте страницу по адресу http://localhost (не через file://), проверьте интернет и консоль (F12).';
                } else if (err.name === 'AbortError') {
                    msg = 'Таймаут запроса (2 мин). Попробуйте файл короче или повторите позже.';
                }
                return { error: msg };
            });
    };

    /** Максимум ошибок подряд — после этого проверки останавливаются. */
    var CONSECUTIVE_ERROR_LIMIT = 3;

    /**
     * Отчёт по проверкам: массив { fileName, success, error?, text?, stage? }.
     * Заполняется в runChecks, используется для отображения и скачивания.
     */
    window.checkReport = [];

    /**
     * Формирует текст общего отчёта для скачивания (.txt).
     * @returns {string}
     */
    window.getCheckReportText = function () {
        var report = window.checkReport;
        if (!report || report.length === 0) return 'Нет данных отчёта.\n';

        var lines = [
            '=== Отчёт проверки аудио ===',
            'Дата: ' + new Date().toLocaleString('ru-RU'),
            'Всего записей: ' + report.length,
            ''
        ];

        report.forEach(function (entry, idx) {
            lines.push('--- ' + (idx + 1) + '. ' + (entry.fileName || 'файл') + ' ---');
            lines.push('Статус: ' + (entry.success ? 'OK' : 'Ошибка'));
            if (entry.stage) lines.push('Этап: ' + entry.stage);
            if (entry.error) lines.push('Ошибка: ' + entry.error);
            if (entry.text) lines.push('Ответ Gemini:\n' + entry.text);
            lines.push('');
        });

        return lines.join('\n');
    };

    /**
     * Скачивает общий отчёт как .txt файл.
     */
    window.downloadCheckReport = function () {
        var text = window.getCheckReportText();
        var blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'audio_check_report_' + new Date().toISOString().slice(0, 10) + '.txt';
        a.click();
        URL.revokeObjectURL(url);
    };

    /**
     * Запускает проверку всех выбранных аудиофайлов через Gemini: загрузка → промпт → удаление с серверов.
     * Логирует каждый запрос и ответ в window.checkReport. Останавливается после CONSECUTIVE_ERROR_LIMIT ошибок подряд.
     * @param {string} apiKey - GEMINI_API_KEY
     * @param {string} modelId - ID модели (например "gemini-2.5-pro")
     * @param {string} prompt - текст промпта для проверки аудио
     * @param {Object} [opts] - опции
     * @param {Array<string>} [opts.fileNames] - имена файлов по порядку (как в selectedAudioLinks)
     * @param {function(Object)} [opts.onProgress] - callback после каждого файла: { index, total, entry }
     */
    window.runChecks = async function (apiKey, modelId, prompt, opts) {
        var links = window.selectedAudioLinks;
        var fileNames = (opts && opts.fileNames) || [];
        var onProgress = (opts && opts.onProgress) || function () {};

        window.checkReport = [];
        var consecutiveErrors = 0;

        for (var i = 0; i < links.length; i++) {
            var link = links[i];
            var fileName = (fileNames[i] !== undefined ? fileNames[i] : 'file_' + (i + 1));
            console.log('Проверяем файл ' + (i + 1) + ' из ' + links.length + ': ' + fileName);

            var uploadResult = await window.uploadToGemini(link, apiKey, 'audio/mp3');
            if (uploadResult.error) {
                var uploadEntry = { fileName: fileName, success: false, error: uploadResult.error, stage: 'upload' };
                window.checkReport.push(uploadEntry);
                consecutiveErrors++;
                onProgress({ index: i, total: links.length, entry: uploadEntry });
                console.error('Ошибка загрузки:', uploadResult.error);
                if (consecutiveErrors >= CONSECUTIVE_ERROR_LIMIT) {
                    console.error('Остановка: ' + CONSECUTIVE_ERROR_LIMIT + ' ошибки подряд.');
                    break;
                }
                continue;
            }

            var filePart = {
                fileData: {
                    fileUri: uploadResult.fileUri,
                    mimeType: uploadResult.mimeType
                }
            };

            var geminiResult = await window.callGemini({
                modelId: modelId,
                apiKey: apiKey,
                prompt: prompt,
                extraParts: [filePart]
            });

            await window.deleteFromGemini(uploadResult.name, apiKey);

            if (geminiResult.error) {
                var errEntry = { fileName: fileName, success: false, error: geminiResult.error, stage: 'gemini' };
                window.checkReport.push(errEntry);
                consecutiveErrors++;
                onProgress({ index: i, total: links.length, entry: errEntry });
                console.error('Ошибка проверки:', geminiResult.error);
                if (consecutiveErrors >= CONSECUTIVE_ERROR_LIMIT) {
                    console.error('Остановка: ' + CONSECUTIVE_ERROR_LIMIT + ' ошибки подряд.');
                    break;
                }
            } else {
                consecutiveErrors = 0;
                var okEntry = { fileName: fileName, success: true, text: geminiResult.text || '' };
                window.checkReport.push(okEntry);
                onProgress({ index: i, total: links.length, entry: okEntry });
                console.log('Результат проверки:', geminiResult.text);
            }
        }

        console.log('Проверка завершена. Обработано: ' + window.checkReport.length + ' из ' + links.length);
    };
})();
