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

        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
            .then(function (res) {
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
                var msg = err && err.message ? err.message : String(err);
                if (msg === 'Failed to fetch' || err instanceof TypeError) {
                    msg = 'Нет связи с сервером. Проверьте интернет и CORS.';
                }
                return { error: msg };
            });
    };
})();
