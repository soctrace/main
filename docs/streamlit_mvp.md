# SocTrace Streamlit MVP

## 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 2. Configurar base de datos

Opcion A (recomendada): variable de entorno

```bash
export DATABASE_URL="postgresql:///mijas"
```

Opcion B: usar `config/settings.yml` con `project.database`.

## 3. Configurar acceso basico

```bash
export SOCTRACE_APP_USERNAME="admin"
export SOCTRACE_APP_PASSWORD="cambia-esta-password"
```

Si no defines estas variables, se usa un acceso demo por defecto.

## 4. Ejecutar la app

```bash
streamlit run app/Home.py
```

## 5. Datos requeridos

- `marts.mijas_features_panel`
- `core.seccion` con geometria `geom`
