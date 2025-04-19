# Klaviyo Analyzer

![Python](https://img.shields.io/badge/python-3.8%2B-blue) 
![License](https://img.shields.io/badge/license-MIT-green) 
![Status](https://img.shields.io/badge/status-active-brightgreen) 
![Dependabot](https://img.shields.io/badge/dependabot-enabled-brightgreen) 
![Last Commit](https://img.shields.io/github/last-commit/rcorzogutierrez/Klaviyo-Analyzer) 
![Repo Size](https://img.shields.io/github/repo-size/rcorzogutierrez/Klaviyo-Analyzer)

Herramienta para analizar métricas de campañas de marketing enviadas a través de Klaviyo. Permite cargar campañas dentro de un rango de fechas, visualizar métricas clave como Open Rate, Click Rate, Total Value, y exportar reportes en formatos ZIP o CSV.

## Características
- Carga campañas de Klaviyo dentro de un rango de fechas especificado.
- Visualiza métricas detalladas: Open Rate, Click Rate, Delivered, Unique Orders, Total Value (en USD y moneda local), y más.
- Convierte valores a moneda local usando tasas de cambio actualizadas.
- Exporta reportes en formatos ZIP y CSV.
- Previsualiza templates de campañas.

## Requisitos previos
- Python 3.8 o superior.
- Un entorno virtual (recomendado).
- Claves API de Klaviyo y Open Exchange Rates (para tasas de cambio).
- Dependencias listadas en `requirements.txt` (si lo generas).

## Instalación
1. **Clona el repositorio**:
   ```bash
   git clone https://github.com/rcorzgutierrez/Klaviyo-Analyzer.git
   cd Klaviyo-Analyzer
   ```
2. **Crea y activa un entorno virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Linux/Mac
   venv\Scripts\activate     # En Windows
   ```
3. **Instala las dependencias**:
   - Si tienes un `requirements.txt`:
     ```bash
     pip install -r requirements.txt
     ```
   - Si no, instala manualmente las dependencias necesarias:
     ```bash
     pip install requests tkcalendar
     ```
   - Nota: Es posible que necesites otras dependencias según tu configuración (e.g., `pandas` si exportas a CSV).
4. **Configura las claves API**:
   - Crea un archivo `.env` o `secrets.py` con tus claves API:
     ```plaintext
     KLAVIYO_API_KEY=tu_clave_aqui
     OPENEXCHANGERATES_API_KEY=tu_clave_aqui
     ```
   - Asegúrate de que estos archivos estén en `.gitignore` para no subirlos al repositorio.

## Uso
1. **Ejecuta la aplicación**:
   ```bash
   python gui.py
   ```
2. **Selecciona un rango de fechas**:
   - Usa la interfaz gráfica para elegir las fechas de inicio y fin.
3. **Visualiza las métricas**:
   - La tabla mostrará métricas como Open Rate, Click Rate, Delivered, Total Value (USD y local), y más.
4. **Exporta reportes**:
   - Usa las opciones de exportación para generar archivos ZIP o CSV.
5. **Previsualiza templates**:
   - Haz clic en una campaña para previsualizar su template.

## Estructura del proyecto
- `campaign_logic.py`: Lógica principal para obtener y procesar campañas de Klaviyo.
- `config.py`: Configuraciones globales (e.g., URLs, códigos de países, símbolos de monedas).
- `exchange_rates.py`: Funciones para obtener tasas de cambio desde Open Exchange Rates.
- `gui.py`: Interfaz gráfica usando Tkinter.
- `klaviyo_api.py`: Funciones para interactuar con la API de Klaviyo.
- `utils.py`: Utilidades como formato de números y porcentajes, manejo de fechas, y funciones de exportación.
- `.gitignore`: Ignora archivos sensibles y generados (`.env`, `secrets.py`, `venv/`, etc.).

## Dependencias
- `requests`: Para hacer solicitudes a las APIs de Klaviyo y Open Exchange Rates.
- `tkcalendar`: Para la selección de fechas en la interfaz gráfica.
- (Opcional) `pandas`: Si usas exportación a CSV.
- (Opcional) Otras dependencias que puedes listar ejecutando:
  ```bash
  pip freeze > requirements.txt
  ```

## Notas
- Asegúrate de que las claves API estén configuradas correctamente en `.env` o `secrets.py`.
- El proyecto está diseñado para manejar monedas locales basadas en códigos de países (e.g., USD, HNL, DOP). Configura las monedas soportadas en `config.py`.
- Los valores monetarios se muestran sin decimales (e.g., "$7,370,048") para mayor claridad.

## Convertir a una Aplicación de Escritorio

Puedes empaquetar esta aplicación en un ejecutable de escritorio para que los usuarios puedan ejecutarla sin instalar Python. Para esto, usaremos **PyInstaller**.

### Pasos para Convertir

1. **Instala PyInstaller**:
   Asegúrate de estar en el entorno virtual (si lo estás usando) e instala PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. **Empaqueta la Aplicación**:
   Desde el directorio del proyecto, ejecuta el siguiente comando para crear un ejecutable:
   ```bash
   pyinstaller --name KlaviyoAnalyzer --windowed --onefile gui.py
   ```
   - `--name KlaviyoAnalyzer`: Nombre del ejecutable.
   - `--windowed`: Indica que es una aplicación GUI (evita que se abra una consola en Windows).
   - `--onefile`: Empaqueta todo en un solo archivo ejecutable.
   - `gui.py`: El archivo principal de la aplicación.

3. **Encuentra el Ejecutable**:
   - Una vez que PyInstaller termine, el ejecutable estará en el directorio `dist/`.
   - Por ejemplo, en Windows será `dist/KlaviyoAnalyzer.exe`, y en macOS/Linux será `dist/KlaviyoAnalyzer`.

4. **Ejecuta el Ejecutable**:
   - Haz doble clic en el ejecutable para abrir la aplicación.
   - Si estás en Linux o macOS, es posible que necesites darle permisos de ejecución primero:
     ```bash
     chmod +x dist/KlaviyoAnalyzer
     ./dist/KlaviyoAnalyzer
     ```

### Notas Importantes
- **Dependencias de Sistema**: En algunos sistemas operativos (como macOS o Linux), `pywebview` puede requerir dependencias adicionales para funcionar correctamente (por ejemplo, `webkit2gtk` en Linux). Consulta la documentación de `pywebview` si encuentras problemas.
- **Tamaño del Ejecutable**: El ejecutable puede ser grande (~100 MB o más) debido a que incluye Python y todas las bibliotecas necesarias.
- **Configuración**: Asegúrate de que `config.py` esté presente en el mismo directorio que el ejecutable, ya que la aplicación lo necesita para funcionar.

## Contribuir
1. Haz un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus cambios y commitea (`git commit -m "Añade nueva funcionalidad"`).
4. Sube tus cambios (`git push origin feature/nueva-funcionalidad`).
5. Crea un Pull Request en GitHub.

## Licencia
Este proyecto está licenciado bajo la [MIT License](LICENSE).