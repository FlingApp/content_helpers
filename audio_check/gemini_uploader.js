(function () {
    'use strict';

    /**
     * Загружает файл (аудио) во временное хранилище Gemini File API и дожидается его готовности.
     * @param {string|Blob|File} fileSource - Object URL (из window.selectedAudioLinks) или сам объект File.
     * @param {string} apiKey - Ваш GEMINI_API_KEY.
     * @param {string} [mimeType='audio/mp3'] - Тип загружаемого файла.
     * @returns {Promise<{ name: string, fileUri: string, mimeType: string } | { error: string }>} 
     */
    window.uploadToGemini = async function (fileSource, apiKey, mimeType = 'audio/mp3') {
        try {
            // 1. Получаем Blob (сам файл)
            // Если передали Object URL (blob:http://...), скачиваем его из памяти браузера
            let fileBlob = fileSource;
            if (typeof fileSource === 'string' && fileSource.startsWith('blob:')) {
                const response = await fetch(fileSource);
                if (!response.ok) throw new Error('Не удалось прочитать локальный файл.');
                fileBlob = await response.blob();
            }

            // 2. Отправляем файл в Gemini API (используем uploadType=media для сырых байтов)
            const uploadUrl = `https://generativelanguage.googleapis.com/upload/v1beta/files?uploadType=media&key=${apiKey}`;
            const uploadRes = await fetch(uploadUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': mimeType
                },
                body: fileBlob
            });

            if (!uploadRes.ok) {
                const errData = await uploadRes.json().catch(() => ({}));
                const errMsg = (errData.error && errData.error.message) ? errData.error.message : 'HTTP ' + uploadRes.status;
                throw new Error('Ошибка загрузки файла: ' + errMsg);
            }

            const uploadData = await uploadRes.json();
            if (!uploadData.file || !uploadData.file.name) {
                throw new Error('Некорректный ответ от API при загрузке.');
            }

            const fileName = uploadData.file.name; // Внутренний ID файла в Gemini (напр. "files/abc123xyz")

            // 3. Ожидание обработки (Polling)
            // Аудиофайлы требуют времени на обработку серверами Google перед тем как их можно скармливать модели.
            while (true) {
                const checkUrl = `https://generativelanguage.googleapis.com/v1beta/${fileName}?key=${apiKey}`;
                const checkRes = await fetch(checkUrl, { method: 'GET' });
                
                if (!checkRes.ok) throw new Error('Ошибка при проверке статуса загруженного файла.');
                const checkData = await checkRes.json();

                if (checkData.state === 'ACTIVE') {
                    // Файл готов! Возвращаем данные, необходимые для отправки промпта
                    return {
                        name: checkData.name,           // нужен для удаления
                        fileUri: checkData.uri,         // нужен для промпта
                        mimeType: checkData.mimeType    // нужен для промпта
                    };
                } else if (checkData.state === 'FAILED') {
                    throw new Error('Gemini не смог обработать этот аудиофайл (статус FAILED).');
                }

                // Если статус PROCESSING, ждем 2 секунды и проверяем снова
                await new Promise(resolve => setTimeout(resolve, 3000));
            }

        } catch (err) {
            return { error: err.message || String(err) };
        }
    };

    /**
     * Удаляет файл из хранилища Gemini. 
     * Рекомендуется вызывать после того, как получен ответ на промпт.
     * @param {string} fileName - Имя файла (из ответа uploadToGemini, например "files/abc123xyz").
     * @param {string} apiKey - Ваш GEMINI_API_KEY.
     */
    window.deleteFromGemini = async function (fileName, apiKey) {
        try {
            const deleteUrl = `https://generativelanguage.googleapis.com/v1beta/${fileName}?key=${apiKey}`;
            const res = await fetch(deleteUrl, { method: 'DELETE' });
            if (!res.ok) {
                console.warn(`Не удалось удалить файл ${fileName} (HTTP ${res.status})`);
            }
        } catch (e) {
            console.error('Ошибка при удалении файла из Gemini:', e);
        }
    };

})();