---
name: i18n
description: Internationalization and localization setup. TRIGGER when the user asks to add translations, internationalize an app, set up i18n/l10n, support multiple languages, or localize content.
---
# Internationalization (i18n)

Set up internationalization and localization to support multiple languages and locales.

## Steps

1. **Assess the current state** - Identify the framework and check if any i18n setup exists.
2. **Choose an i18n library** - Select the right tool for the stack.
3. **Extract strings** - Replace hardcoded strings with translation keys.
4. **Create translation files** - Set up the default locale and at least one additional locale.
5. **Configure locale detection** - Set up automatic locale detection (URL, browser, user preference).
6. **Handle formatting** - Set up number, date, and currency formatting per locale.
7. **Test** - Verify translations load correctly and switching locales works.

## Library Selection

| Stack | Library |
|-------|---------|
| React | react-intl, react-i18next, next-intl |
| Vue | vue-i18n |
| Angular | @angular/localize, ngx-translate |
| Node.js | i18next |
| Python/Django | Django built-in i18n |
| Python/Flask | Flask-Babel |
| Go | go-i18n |

## React (react-i18next)

### Setup
```bash
npm install i18next react-i18next i18next-browser-languagedetector i18next-http-backend
```

```typescript
// i18n.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: {
          welcome: 'Welcome, {{name}}!',
          items_count: '{{count}} item',
          items_count_plural: '{{count}} items',
          nav: {
            home: 'Home',
            about: 'About',
            contact: 'Contact',
          },
        },
      },
      es: {
        translation: {
          welcome: 'Bienvenido, {{name}}!',
          items_count: '{{count}} artículo',
          items_count_plural: '{{count}} artículos',
          nav: {
            home: 'Inicio',
            about: 'Acerca de',
            contact: 'Contacto',
          },
        },
      },
    },
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  });

export default i18n;
```

### Usage in Components
```tsx
import { useTranslation } from 'react-i18next';

function Header() {
  const { t, i18n } = useTranslation();

  return (
    <header>
      <h1>{t('welcome', { name: 'Alice' })}</h1>
      <nav>
        <a href="/">{t('nav.home')}</a>
        <a href="/about">{t('nav.about')}</a>
      </nav>
      <select
        value={i18n.language}
        onChange={(e) => i18n.changeLanguage(e.target.value)}
      >
        <option value="en">English</option>
        <option value="es">Español</option>
      </select>
    </header>
  );
}
```

## Next.js (next-intl)

### Setup
```typescript
// messages/en.json
{
  "home": {
    "title": "Welcome to our site",
    "description": "Find everything you need"
  }
}

// messages/es.json
{
  "home": {
    "title": "Bienvenido a nuestro sitio",
    "description": "Encuentra todo lo que necesitas"
  }
}

// i18n.ts
import { getRequestConfig } from 'next-intl/server';

export default getRequestConfig(async ({ locale }) => ({
  messages: (await import(`./messages/${locale}.json`)).default,
}));
```

## Django (Python)

```python
# settings.py
LANGUAGE_CODE = 'en'
USE_I18N = True
USE_L10N = True

LANGUAGES = [
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'Français'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

MIDDLEWARE = [
    ...
    'django.middleware.locale.LocaleMiddleware',
    ...
]
```

```python
# views.py
from django.utils.translation import gettext as _

def home(request):
    message = _("Welcome to our site")
    return render(request, 'home.html', {'message': message})
```

```html
<!-- templates/home.html -->
{% load i18n %}
<h1>{% trans "Welcome to our site" %}</h1>
<p>{% blocktrans count items=cart_count %}
  {{ items }} item in your cart.
{% plural %}
  {{ items }} items in your cart.
{% endblocktrans %}</p>
```

```bash
# Extract strings and create translation files
python manage.py makemessages -l es
python manage.py makemessages -l fr

# Compile translations
python manage.py compilemessages
```

## Translation File Structure

```
locales/
├── en/
│   ├── common.json      # Shared strings (nav, buttons, errors)
│   ├── home.json        # Home page strings
│   └── auth.json        # Auth-related strings
├── es/
│   ├── common.json
│   ├── home.json
│   └── auth.json
└── fr/
    ├── common.json
    ├── home.json
    └── auth.json
```

## Date, Number, and Currency Formatting

```javascript
// Use Intl API for locale-aware formatting
const date = new Date('2025-03-15');

// Date
new Intl.DateTimeFormat('en-US').format(date);  // "3/15/2025"
new Intl.DateTimeFormat('de-DE').format(date);  // "15.3.2025"

// Number
new Intl.NumberFormat('en-US').format(1234567.89);  // "1,234,567.89"
new Intl.NumberFormat('de-DE').format(1234567.89);  // "1.234.567,89"

// Currency
new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(42.5);  // "$42.50"
new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(42);    // "¥42"
```

## Rules

- Never concatenate translated strings -- use interpolation (`t('hello', { name })` not `t('hello') + name`)
- Handle plurals correctly using the i18n library's plural system, not if/else
- Use ICU message format or the library's plural syntax for complex pluralization
- Keep translation keys descriptive and namespaced (`auth.login.button`, not `btn1`)
- Provide context for translators via comments or description fields
- Do not hardcode text direction -- use CSS `direction` and logical properties (`margin-inline-start`)
- Always use `Intl` APIs for date, number, and currency formatting -- never format manually
- Set the `lang` attribute on the HTML element to match the current locale
- Test with RTL languages (Arabic, Hebrew) to catch layout issues
