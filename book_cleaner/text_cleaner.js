// Элементы интерфейса
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const runBtn = document.getElementById('run-btn');
const downloadBtn = document.getElementById('download-btn');
const resetBtn = document.getElementById('reset-btn'); // Новая кнопка
const logContainer = document.getElementById('log-container');
const logList = document.getElementById('log-list');

let currentFile = null;
let originalText = '';
let cleanedText = '';
let fileLog = [];

// --- Настройка Drag & Drop и выбора файла ---

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFileSelection(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFileSelection(e.target.files[0]);
    }
});

function handleFileSelection(file) {
    if (!file.name.endsWith('.txt')) {
        alert('Пожалуйста, выберите файл формата .txt');
        return;
    }
    currentFile = file;
    fileInfo.textContent = `Выбран файл: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    
    // Обновляем видимость кнопок
    runBtn.disabled = false;
    resetBtn.style.display = 'inline-block'; // Показываем кнопку сброса
    downloadBtn.style.display = 'none';
    logContainer.style.display = 'none';
}

// --- Логика очистки текста ---

runBtn.addEventListener('click', () => {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        originalText = e.target.result;
        processText();
    };
    
    reader.readAsText(currentFile);
});

function processText() {
    fileLog = [];
    const lines = originalText.split('\n');
    let resultLines = [];
    let emptyLineCount = 0;

    lines.forEach((line, index) => {
        let lineNumber = index + 1;
        let lineChanges =[];

        // СНАЧАЛА тихо удаляем Windows-символ возврата каретки (\r), 
        // чтобы JS не принимал его за "лишний пробел в конце строки"
        line = line.replace(/\r/g, '');

        // 1. Поиск и удаление скрытых символов
        if (/[\u200B\uFEFF\u200E\u200F]/.test(line)) {
            line = line.replace(/[\u200B\uFEFF\u200E\u200F]/g, '');
            lineChanges.push('удален скрытый символ');
        }

        // 2. Лишние пробелы в начале и конце
        if (line.trim() !== line) {
            line = line.trim(); 
            lineChanges.push('удалены пробелы по краям');
        }

        // 3. Двойные пробелы между словами
        if (/ {2,}/.test(line)) {
            line = line.replace(/ {2,}/g, ' ');
            lineChanges.push('двойные пробелы заменены на один');
        }

        // 4. Логика множественных переносов
        if (line === '') {
            emptyLineCount++;
            if (emptyLineCount > 1) {
                fileLog.push(`Строка ${lineNumber}: удален лишний перенос строки`);
                return; // Пропускаем добавление этой строки
            }
        } else {
            emptyLineCount = 0;
        }

        if (lineChanges.length > 0) {
            fileLog.push(`Строка ${lineNumber}: ${lineChanges.join(', ')}`);
        }

        resultLines.push(line);
    });

    cleanedText = resultLines.join('\n');
    showResults();
}

// --- Отображение результатов и скачивание ---

function showResults() {
    logList.innerHTML = '';
    logContainer.style.display = 'block';

    if (fileLog.length === 0) {
        logList.innerHTML = '<li class="success-msg">Файл идеален! Никаких проблем не найдено.</li>';
    } else {
        const displayLimit = 150; 
        const logsToShow = fileLog.slice(0, displayLimit);
        
        logsToShow.forEach(logText => {
            const li = document.createElement('li');
            li.textContent = logText;
            logList.appendChild(li);
        });

        if (fileLog.length > displayLimit) {
            const li = document.createElement('li');
            li.innerHTML = `<em>... и еще ${fileLog.length - displayLimit} исправлений скрыто.</em>`;
            li.style.color = '#333';
            logList.appendChild(li);
        }
    }

    downloadBtn.style.display = 'inline-block';
    downloadBtn.onclick = createDownload;
}

function createDownload() {
    const blob = new Blob([cleanedText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const newFileName = currentFile.name.replace('.txt', '_cleaned.txt');

    const a = document.createElement('a');
    a.href = url;
    a.download = newFileName;
    document.body.appendChild(a);
    a.click();
    
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// --- Функция сброса (Reset) ---
resetBtn.addEventListener('click', () => {
    // Очищаем переменные
    currentFile = null;
    originalText = '';
    cleanedText = '';
    fileLog = [];

    // Возвращаем интерфейс в исходное состояние
    fileInput.value = ''; // Сбрасываем input (чтобы можно было загрузить тот же файл еще раз)
    fileInfo.textContent = ''; // Очищаем имя файла
    
    // Прячем/блокируем кнопки
    runBtn.disabled = true;
    resetBtn.style.display = 'none';
    downloadBtn.style.display = 'none';
    
    // Прячем логи
    logContainer.style.display = 'none';
    logList.innerHTML = '';
});