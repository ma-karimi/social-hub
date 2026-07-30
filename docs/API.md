# SocialHub API — راهنمای استفاده

این سند نحوهٔ کار با API پروژه **SocialHub** را توضیح می‌دهد. SocialHub یک پلتفرم چند-مستأجری (Multi-Tenant) برای انتشار محتوا در شبکه‌های اجتماعی است و در کنار پروژهٔ جداگانهٔ **telegram-bot** قرار دارد.

| پروژه | نقش |
|-------|-----|
| **social-hub** | API مرکزی — مدیریت tenant، اتصال پلتفرم‌ها، انتشار/ویرایش/حذف پست |
| **telegram-bot** | ربات تلگرام مستقل (legacy) — برای پشتیبانی و تعامل مستقیم با کاربر |

برای انتشار خودکار در کانال تلگرام از **SocialHub** استفاده کنید؛ `telegram-bot` مسیر جداگانه‌ای است.

---

## شروع سریع

### ۱. راه‌اندازی سرویس

```bash
cd social-hub
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# DATABASE_URL، REDIS_URL و ENCRYPTION_KEY را تنظیم کنید

createdb socialhub
alembic upgrade head

# ترمینال ۱ — API
uvicorn social_hub.main:app --reload --port 8000

# ترمینال ۲ — Worker (پردازش صف انتشار)
arq social_hub.infrastructure.queue.worker.WorkerSettings
```

### ۲. Import در Postman

1. **File → Import**
2. فایل‌ها را import کنید:
   - `docs/postman/SocialHub.postman_collection.json`
   - `docs/postman/SocialHub.postman_environment.json`
3. Environment **SocialHub — Local** را انتخاب کنید.
4. متغیر `base_url` را در صورت نیاز تغییر دهید (پیش‌فرض: `http://localhost:8000`).

### ۳. جریان کاری پیشنهادی (Quick Start folder)

در Postman این ترتیب را دنبال کنید:

```
Health Check
  → Create Tenant          (api_key و tenant_id خودکار ذخیره می‌شود)
  → Create Telegram Connection
  → Test Connection
  → Publish Product Post
  → Get Post Status
```

---

## احراز هویت

| Endpoint | Header | توضیح |
|----------|--------|-------|
| `/health` | — | بدون احراز هویت |
| `/api/v1/tenants/*` | — | بدون احراز هویت (در production محدود کنید) |
| `/api/v1/connections/*` | `X-API-Key: <api_key>` | کلید tenant |
| `/api/v1/posts/*` | `X-API-Key: <api_key>` | کلید tenant |
| `/api/v1/webhooks/telegram/*` | `X-Telegram-Bot-Api-Secret-Token` | secret ثبت‌شده در connection |
| `/api/v1/webhooks/bale/*` | `X-Webhook-Secret` یا `?secret=` | secret ثبت‌شده در connection |

کلید API فقط **یک‌بار** هنگام `Create Tenant` یا `Regenerate API Key` برگردانده می‌شود.

---

## Endpointها

Base URL: `{base_url}/api/v1`

### Health

| Method | Path | Auth | توضیح |
|--------|------|------|-------|
| GET | `/health` | — | وضعیت سرویس |

**Response 200:**
```json
{ "status": "ok" }
```

---

### Tenants

| Method | Path | Auth | Status | توضیح |
|--------|------|------|--------|-------|
| POST | `/tenants` | — | 201 | ایجاد tenant جدید |
| GET | `/tenants` | — | 200 | لیست tenantها |
| GET | `/tenants/{tenant_id}` | — | 200 | جزئیات tenant |
| POST | `/tenants/{tenant_id}/regenerate-key` | — | 200 | چرخش API key |

**Create Tenant — Request:**
```json
{
  "name": "My Store",
  "settings": {
    "webhook_callback_url": "https://panel.example.com/webhooks/socialhub"
  }
}
```

**Create Tenant — Response 201:**
```json
{
  "tenant": {
    "id": "uuid",
    "name": "My Store",
    "is_active": true,
    "settings": { "webhook_callback_url": "..." }
  },
  "api_key": "sh_xxxxxxxx"
}
```

`webhook_callback_url` اختیاری است — وقتی کاربر روی دکمهٔ inline کلیک کند، SocialHub رویداد را به این URL POST می‌کند.

---

### Connections

| Method | Path | Auth | Status | توضیح |
|--------|------|------|--------|-------|
| POST | `/connections` | X-API-Key | 201 | اتصال پلتفرم جدید |
| GET | `/connections` | X-API-Key | 200 | لیست اتصال‌ها |
| PATCH | `/connections/{connection_id}` | X-API-Key | 200 | به‌روزرسانی |
| DELETE | `/connections/{connection_id}` | X-API-Key | 204 | حذف |
| POST | `/connections/{connection_id}/test` | X-API-Key | 200 | تست اتصال |

**پلتفرم‌های پشتیبانی‌شده:** `telegram`, `bale`, `eitaa`, `instagram`, `whatsapp`, `twitter`

**Create Telegram Connection — Request:**
```json
{
  "platform_type": "telegram",
  "credentials": {
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
  },
  "settings": {
    "channel_id": "@your_channel",
    "webhook_secret": "my-secret-token"
  }
}
```

| فیلد | الزامی | توضیح |
|------|--------|-------|
| `credentials.bot_token` | بله | توکن BotFather |
| `settings.channel_id` | بله | `@username` یا `-100...` کانال |
| `settings.webhook_secret` | توصیه‌شده | secret برای verify webhook تلگرام |

**Create Bale Connection — Request:**
```json
{
  "platform_type": "bale",
  "credentials": {
    "bot_token": "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
  },
  "settings": {
    "channel_id": "@your_bale_channel",
    "webhook_secret": "my-secret-token"
  }
}
```

| فیلد | الزامی | توضیح |
|------|--------|-------|
| `credentials.bot_token` | بله | توکن بازوی بله (از پنل بله) |
| `settings.channel_id` | بله | `@username` یا شناسهٔ عددی کانال/چت |
| `settings.webhook_secret` | توصیه‌شده | برای verify؛ با هدر `X-Webhook-Secret` یا `?secret=` |

> API بله روی `https://tapi.bale.ai/bot{token}` است و با Bot API تلگرام سازگار است. هر tenant فقط یک connection برای هر `platform_type` می‌تواند داشته باشد.

**Create Eitaa Connection — Request:**
```json
{
  "platform_type": "eitaa",
  "credentials": {
    "bot_token": "bot511500:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  },
  "settings": {
    "channel_id": "your_eitaa_channel",
    "title": "عنوان پنل ایتایار",
    "pin": false,
    "disable_notification": false
  }
}
```

| فیلد | الزامی | توضیح |
|------|--------|-------|
| `credentials.bot_token` | بله | توکن ایتایار (از پنل [eitaayar.ir](https://eitaayar.ir)) |
| `settings.channel_id` | بله | شناسهٔ عددی کانال یا username **بدون** `@` |
| `settings.title` | خیر | عنوان مطلب فقط برای پنل ایتایار |
| `settings.pin` | خیر | سنجاق کردن پیام پس از ارسال |
| `settings.disable_notification` | خیر | ارسال بدون نوتیفیکیشن |
| `settings.view_count_for_delete` | خیر | حذف خودکار پس از N بازدید |

> API ایتا از طریق ایتایار روی `https://eitaayar.ir/api/{token}/{method}` کار می‌کند و فقط انتشار (`sendMessage` / `sendFile`) را پشتیبانی می‌کند — ویرایش، حذف، دکمهٔ inline و webhook ورودی ندارد. کاربر [`@sender`](https://eitaa.com/sender) باید مدیر کانال/گروه باشد.

**Test Connection — Response:**
```json
{ "ok": true, "bot": { "id": 123, "username": "mybot", "first_name": "My Bot" } }
```

---

### Posts

| Method | Path | Auth | Status | توضیح |
|--------|------|------|--------|-------|
| POST | `/posts/publish-product` | X-API-Key | 202 | انتشار پست محصول |
| POST | `/posts/publish` | X-API-Key | 202 | انتشار پست عادی |
| PATCH | `/posts/{post_id}` | X-API-Key | 202 | ویرایش |
| DELETE | `/posts/{post_id}` | X-API-Key | 202 | حذف |
| GET | `/posts/{post_id}` | X-API-Key | 200 | وضعیت |
| GET | `/posts?limit=50&offset=0` | X-API-Key | 200 | لیست |

> پاسخ **202 Accepted** یعنی job در صف Redis قرار گرفته — worker باید در حال اجرا باشد.

**Publish Product — Request:**
```json
{
  "platforms": ["telegram"],
  "content": {
    "title": "محصول نمونه",
    "body": "توضیحات محصول",
    "price": 150000,
    "currency": "IRR",
    "images": ["https://example.com/product.jpg"],
    "metadata": {}
  },
  "buttons": [
    {
      "action": "buy",
      "label": "خرید",
      "payload": { "product_id": 42 }
    },
    {
      "action": "url",
      "label": "مشاهده در سایت",
      "payload": { "url": "https://shop.example.com/products/42" }
    }
  ],
  "external_ref": "product-42"
}
```

**انواع action برای دکمه‌ها:**

| action | payload | رفتار |
|--------|---------|-------|
| `buy` | `{ "product_id": N }` | callback inline |
| `product_details` | `{ "product_id": N }` | callback inline |
| `add_to_cart` | `{ "product_id": N }` | callback inline |
| `specifications` | `{ "product_id": N }` | callback inline |
| `contact` | `{}` | callback inline |
| `url` | `{ "url": "https://..." }` | دکمهٔ لینک |

**Publish — Response 202:**
```json
{
  "post_id": "uuid",
  "publications": [
    { "id": "uuid", "status": "pending", "connection_id": "uuid" }
  ],
  "warnings": []
}
```

**Get Post — Response 200:**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "post_type": "product",
  "status": "published",
  "external_ref": "product-42",
  "publications": [
    { "id": "uuid", "status": "published", "connection_id": "uuid" }
  ]
}
```

**خطاهای رایج:**

| Status | علت |
|--------|-----|
| 401 | `X-API-Key` ناقص یا نامعتبر |
| 404 | post/connection پیدا نشد |
| 409 | `external_ref` تکراری |
| 422 | پلتفرم بدون connection فعال |

---

### Webhooks

| Method | Path | Auth | توضیح |
|--------|------|------|-------|
| POST | `/webhooks/telegram/{connection_id}` | Secret Token | دریافت update از تلگرام |
| POST | `/webhooks/bale/{connection_id}` | Query/Header secret | دریافت update از بله |

این endpointها را **پلتفرم** صدا می‌زند، نه کلاینت شما.

**ثبت webhook در تلگرام:**

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/api/v1/webhooks/telegram/<CONNECTION_ID>",
    "secret_token": "my-secret-token"
  }'
```

`secret_token` باید با `settings.webhook_secret` connection یکسان باشد.

**ثبت webhook در بله:**

```bash
curl -X POST "https://tapi.bale.ai/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/api/v1/webhooks/bale/<CONNECTION_ID>?secret=my-secret-token"
  }'
```

بله `secret_token` هدر ندارد؛ secret را در query (`?secret=`) یا هدر `X-Webhook-Secret` بگذارید تا با `settings.webhook_secret` مطابقت کند.

وقتی کاربر روی دکمهٔ inline کلیک کند:
1. پلتفرم update را به SocialHub می‌فرستد
2. Worker رویداد را پردازش می‌کند
3. اگر `webhook_callback_url` در tenant تنظیم شده باشد، رویداد به پنل شما POST می‌شود

---

## مثال cURL (بدون Postman)

```bash
# 1. ایجاد tenant
curl -s -X POST http://localhost:8000/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Store"}' | jq .

# 2. اتصال تلگرام (API_KEY را جایگزین کنید)
curl -s -X POST http://localhost:8000/api/v1/connections \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "platform_type": "telegram",
    "credentials": {"bot_token": "YOUR_BOT_TOKEN"},
    "settings": {"channel_id": "@your_channel", "webhook_secret": "secret123"}
  }' | jq .

# 2b. اتصال بله
curl -s -X POST http://localhost:8000/api/v1/connections \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "platform_type": "bale",
    "credentials": {"bot_token": "YOUR_BALE_BOT_TOKEN"},
    "settings": {"channel_id": "@your_bale_channel", "webhook_secret": "secret123"}
  }' | jq .

# 2c. اتصال ایتا (ایتایار)
curl -s -X POST http://localhost:8000/api/v1/connections \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "platform_type": "eitaa",
    "credentials": {"bot_token": "YOUR_EITAAYAR_TOKEN"},
    "settings": {"channel_id": "your_eitaa_channel"}
  }' | jq .

# 3. انتشار محصول
curl -s -X POST http://localhost:8000/api/v1/posts/publish-product \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "platforms": ["telegram"],
    "content": {
      "title": "Test",
      "body": "Hello channel",
      "price": 100000,
      "currency": "IRR",
      "images": ["https://picsum.photos/400"]
    },
    "buttons": [{"action": "buy", "label": "Buy", "payload": {"product_id": 1}}]
  }' | jq .

# 4. وضعیت پست
curl -s http://localhost:8000/api/v1/posts/$POST_ID \
  -H "X-API-Key: $API_KEY" | jq .
```

---

## OpenAPI / Swagger

با اجرای API، مستندات تعاملی در دسترس است:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## نکات production

1. endpointهای `/tenants` را پشت firewall یا admin auth قرار دهید.
2. `WEBHOOK_BASE_URL` را در `.env` تنظیم کنید.
3. worker (`arq`) باید همیشه در حال اجرا باشد.
4. `ENCRYPTION_KEY` را rotate نکنید مگر با migration credentials.
5. برای HTTPS از reverse proxy (nginx/caddy) استفاده کنید — webhook تلگرام HTTPS می‌خواهد.

---

## فایل‌های Postman

| فایل | مسیر |
|------|------|
| Collection | `docs/postman/SocialHub.postman_collection.json` |
| Environment | `docs/postman/SocialHub.postman_environment.json` |

Collection شامل test script است که پس از Create Tenant و Create Connection، متغیرهای `api_key`، `tenant_id`، `connection_id` و `post_id` را خودکار set می‌کند.
