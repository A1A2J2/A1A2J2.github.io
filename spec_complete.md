# LLM Chatbot Service - COMPLETE SPECIFICATION

## PROJECT SUMMARY
Build a web-based SaaS chatbot platform where users can chat with multiple open-source LLM models (Llama 7B, Qwen2 7B, 14B, 32B). Monetize through:
- **Free Tier**: Limited monthly uses per model
- **Paid Tier**: $19/month subscription for higher limits and unlimited small model access

Backend: Python (FastAPI)
Frontend: Single-page app (HTML/CSS/JavaScript)
LLM Backend: Ollama (runs on M2 Mac Air)
Database: SQLite (simple, local)
Payments: Stripe API
Hosting: DigitalOcean App Platform or similar VPS

---

## DETAILED REQUIREMENTS

### 1. USER AUTHENTICATION & ACCOUNTS

#### Signup Flow
- **Endpoint**: `POST /api/auth/signup`
- **Request Body**:
  ```json
  {
    "username": "string (3-20 chars, alphanumeric + underscore)",
    "password": "string (min 8 chars, must include 1 uppercase, 1 number)",
    "email": "string (valid email format)"
  }
  ```
- **Validations**:
  - Username must be unique (check database first)
  - Username can only contain letters, numbers, underscores
  - Email must be valid format
  - Password must be 8+ chars with uppercase + number
  - Reject if username already exists (return 409 Conflict)
- **Response**:
  ```json
  {
    "status": "success",
    "user_id": "integer",
    "username": "string",
    "tier": "free",
    "message": "Account created successfully"
  }
  ```
- **Hash password** using bcrypt (salt rounds: 12)
- **Create user** in database with:
  - user_id (auto-increment)
  - username
  - password_hash
  - email
  - tier = "free"
  - created_at = current timestamp
  - stripe_customer_id = NULL
  - subscription_id = NULL
  - last_tier_reset = current date

#### Login Flow
- **Endpoint**: `POST /api/auth/login`
- **Request Body**:
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Validations**:
  - Check username exists in database
  - Verify password hash matches (bcrypt)
  - Return 401 Unauthorized if either fails
- **Response**:
  ```json
  {
    "status": "success",
    "user_id": "integer",
    "username": "string",
    "tier": "free or paid",
    "token": "JWT token string (expires in 30 days)",
    "email": "string"
  }
  ```
- **Generate JWT token** with:
  - user_id
  - username
  - tier
  - exp (expiration: 30 days from now)
  - iat (issued at)
  - Secret key stored in environment variable

#### Logout Flow
- **Endpoint**: `POST /api/auth/logout`
- **Action**: Client-side deletes JWT from localStorage
- **Backend**: Invalidate token (optional: add to blacklist)

#### Session Check
- **Endpoint**: `GET /api/auth/me`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Validations**:
  - Verify JWT token signature
  - Check token not expired
  - Return 401 if invalid/expired
- **Response**:
  ```json
  {
    "user_id": "integer",
    "username": "string",
    "email": "string",
    "tier": "free or paid",
    "joined_date": "ISO date string"
  }
  ```

#### Password Reset (Optional but recommended)
- **Endpoint**: `POST /api/auth/forgot-password`
- **Request**: `{ "email": "string" }`
- **Action**: Generate temporary reset token, email to user
- **Endpoint**: `POST /api/auth/reset-password`
- **Request**: `{ "token": "string", "new_password": "string" }`
- **Action**: Verify token valid, update password hash

---

### 2. LLM MODELS & CONFIGURATION

#### Available Models
Each model has:
- Model ID (internal name)
- Display name (what users see)
- Free tier monthly limit
- Paid tier monthly limit
- Max tokens (context length)
- Average response time (for UI)

**Model 1: Llama 2 7B**
- Model ID: `llama2_7b`
- Display Name: "Llama 2 7B"
- Free Limit: 100 uses/month
- Paid Limit: Unlimited
- Max Tokens: 2048
- Ollama command: `ollama pull llama2:7b`

**Model 2: Qwen2 7B**
- Model ID: `qwen2_7b`
- Display Name: "Qwen2 7B"
- Free Limit: 100 uses/month (combined with Llama 7B)
- Paid Limit: Unlimited
- Max Tokens: 2048
- Ollama command: `ollama pull qwen2:7b`

**Model 3: Llama 2 14B**
- Model ID: `llama2_14b`
- Display Name: "Llama 2 14B (Faster Responses)"
- Free Limit: 5 uses/month
- Paid Limit: 25 uses/month
- Max Tokens: 4096
- Ollama command: `ollama pull llama2:14b`

**Model 4: Llama 2 32B**
- Model ID: `llama2_32b`
- Display Name: "Llama 2 32B (Most Powerful)"
- Free Limit: 1 use/month
- Paid Limit: 10 uses/month
- Max Tokens: 4096
- Ollama command: `ollama pull llama2:32b`

#### Model Grouping for Tracking
- **Group 1 (7B models)**: llama2_7b + qwen2_7b share 100 free uses/month
- **Group 2 (14B)**: llama2_14b has separate limit
- **Group 3 (32B)**: llama2_32b has separate limit

---

### 3. CHAT & MESSAGE HANDLING

#### Send Message Endpoint
- **Endpoint**: `POST /api/chat/send`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Request Body**:
  ```json
  {
    "message": "string (1-5000 chars)",
    "model_id": "string (llama2_7b, qwen2_7b, llama2_14b, or llama2_32b)",
    "conversation_id": "integer or null (optional, for threading)"
  }
  ```

#### Validations Before Sending to LLM
1. **JWT token valid and not expired**
2. **User exists in database**
3. **Message not empty** (trim whitespace)
4. **Message length** 1-5000 chars
5. **Model ID valid** (must be one of 4 models)
6. **Check usage limits**:
   - Get user's tier (free or paid)
   - Get user's remaining uses for this model's group
   - If remaining uses = 0, return 429 Too Many Requests
   - If remaining < 0, reject request
7. **Rate limiting**:
   - Max 1 request per user per 2 seconds
   - Return 429 if exceeded

#### Call Ollama LLM
- **Ollama API Endpoint**: `http://[M2_MAC_IP]:11434/api/generate`
- **Request to Ollama**:
  ```json
  {
    "model": "model_name",
    "prompt": "user_message",
    "stream": false,
    "temperature": 0.7,
    "top_p": 0.9
  }
  ```
- **Handle Ollama errors**:
  - If M2 offline: return 503 Service Unavailable
  - If model not found: return 404 with helpful message
  - If timeout (>60 seconds): return 504 Gateway Timeout
- **Response from Ollama**:
  ```json
  {
    "response": "string",
    "done": true,
    "context": "array of tokens"
  }
  ```

#### Store in Database & Return to User
- **Create entry in messages table**:
  - message_id (auto-increment)
  - user_id
  - model_used (model_id)
  - user_message (the prompt)
  - ai_response (Ollama output)
  - timestamp (current time)
  - conversation_id (optional)
  - tokens_used (approximate, for tracking)
- **Decrement usage count**:
  - Get current usage for this user/model/month
  - Add 1 to usage_count
  - Store updated usage
- **Response to Frontend**:
  ```json
  {
    "status": "success",
    "message_id": "integer",
    "ai_response": "string (Ollama output)",
    "model_used": "string",
    "timestamp": "ISO datetime",
    "uses_remaining": {
      "llama2_7b_qwen2_7b": "integer (0-100 or unlimited)",
      "llama2_14b": "integer",
      "llama2_32b": "integer"
    }
  }
  ```

#### Chat History Endpoint
- **Endpoint**: `GET /api/chat/history?limit=50&offset=0`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Returns**: Last 50 messages for this user, newest first
- **Response**:
  ```json
  {
    "messages": [
      {
        "message_id": "integer",
        "model_used": "string",
        "user_message": "string",
        "ai_response": "string",
        "timestamp": "ISO datetime"
      }
    ],
    "total_count": "integer"
  }
  ```

#### Delete Message Endpoint (Optional)
- **Endpoint**: `DELETE /api/chat/message/{message_id}`
- **Validates**: User owns this message
- **Action**: Soft delete (set deleted_at timestamp)

---

### 4. USAGE TRACKING & LIMITS

#### Usage Database Schema
```sql
CREATE TABLE usage (
  usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  model_group TEXT NOT NULL, -- '7b', '14b', '32b'
  uses_this_month INTEGER DEFAULT 0,
  month_start_date DATE NOT NULL, -- Day usage resets
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(user_id)
);
```

#### Usage Logic
- **On signup**: Create usage entries for all 3 groups (7b, 14b, 32b)
  - month_start_date = today
  - uses_this_month = 0
- **When user sends message**:
  - Find relevant usage row (user_id + model_group)
  - Increment uses_this_month by 1
  - Update updated_at timestamp
- **Monthly reset**:
  - Every day at 00:00 UTC, run background job
  - For each user, check if month_start_date + 30 days < today
  - If yes: reset uses_this_month to 0, set new month_start_date
  - Alternative: Check on login/each request if reset needed

#### Get Remaining Uses Endpoint
- **Endpoint**: `GET /api/usage/remaining`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Logic**:
  - Get user's tier (free or paid)
  - Fetch usage rows for all 3 groups
  - Calculate remaining = limit - uses_this_month
  - For paid users: show higher limits
  - For free users: show free limits
- **Response**:
  ```json
  {
    "tier": "free or paid",
    "usage": {
      "llama2_7b_qwen2_7b": {
        "used": "integer",
        "limit": "integer or null (unlimited)",
        "remaining": "integer or null"
      },
      "llama2_14b": {
        "used": "integer",
        "limit": "integer",
        "remaining": "integer"
      },
      "llama2_32b": {
        "used": "integer",
        "limit": "integer",
        "remaining": "integer"
      }
    },
    "month_resets_on": "ISO date (e.g., 2024-02-15)"
  }
  ```

---

### 5. PAYMENT & SUBSCRIPTION (STRIPE)

#### Stripe Setup
- Create Stripe account
- Get live API key (keep secret)
- Get publishable key (client-side)
- Create product "Premium Subscription" in Stripe dashboard
- Create price: $19/month, recurring

#### Upgrade to Paid Endpoint
- **Endpoint**: `POST /api/subscription/create-checkout`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Action**:
  - Create Stripe checkout session
  - Set success_url: `https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}`
  - Set cancel_url: `https://yourdomain.com/dashboard`
  - Include user_id in metadata
- **Response**:
  ```json
  {
    "checkout_url": "string (Stripe checkout page)"
  }
  ```
- **Frontend**: Redirect user to checkout_url

#### Handle Stripe Webhook
- **Webhook Event**: `checkout.session.completed`
- **Action**:
  - Verify webhook signature (Stripe secret)
  - Extract user_id from metadata
  - Extract Stripe customer_id and subscription_id
  - Update user in database:
    - tier = "paid"
    - stripe_customer_id = customer_id
    - subscription_id = subscription_id
    - paid_since = current date
  - Send confirmation email to user
- **Webhook Event**: `customer.subscription.deleted`
- **Action**:
  - Extract subscription_id
  - Find user with this subscription_id
  - Update user:
    - tier = "free"
    - subscription_id = NULL
  - Send cancellation email

#### Check Subscription Status Endpoint
- **Endpoint**: `GET /api/subscription/status`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Response**:
  ```json
  {
    "tier": "free or paid",
    "subscription_active": "boolean",
    "next_billing_date": "ISO date or null",
    "cancel_at_period_end": "boolean"
  }
  ```

#### Cancel Subscription Endpoint
- **Endpoint**: `POST /api/subscription/cancel`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Action**:
  - Get user's subscription_id from database
  - Call Stripe API to cancel subscription
  - Update user tier to "free" (but keep access until period end)
  - Set cancel_at_period_end = true in Stripe
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Subscription cancelled. Access remains until [date]."
  }
  ```

#### Manage Billing Portal
- **Endpoint**: `POST /api/subscription/billing-portal`
- **Headers**: `Authorization: Bearer {JWT_TOKEN}`
- **Action**:
  - Create Stripe customer portal session
  - User can manage payment method, view invoices, resubscribe
- **Response**:
  ```json
  {
    "portal_url": "string"
  }
  ```

---

### 6. FRONTEND (HTML/CSS/JAVASCRIPT)

#### Pages & Routes

**Page 1: Login/Signup** (`/`)
- If user already logged in (JWT in localStorage), redirect to /dashboard
- Show two tabs: "Login" and "Sign Up"
- **Login Tab**:
  - Username input
  - Password input
  - "Login" button
  - Error message display
  - "Forgot password?" link
- **Sign Up Tab**:
  - Username input (with validation feedback)
  - Email input
  - Password input (show requirements: 8+ chars, 1 uppercase, 1 number)
  - Confirm password input
  - "Sign Up" button
  - Error message display
  - Terms of service link

**Page 2: Dashboard** (`/dashboard`)
- Require valid JWT, redirect to login if missing
- **Header**:
  - App logo/name on left
  - User's username
  - "Settings" button
  - "Logout" button
- **Main Section**:
  - **Current Tier Card**:
    - Show "Free Tier" or "Paid Tier ($19/month)"
    - If free: show "Upgrade to Paid" button
    - If paid: show "Manage Subscription" button
  - **Usage Summary Cards** (3 cards):
    - **Card 1**: Llama 7B + Qwen2 7B
      - Display: "100/100 uses" (or "Unlimited")
      - Progress bar
    - **Card 2**: Llama 14B
      - Display: "5/5 uses" or "25/25 uses" (free vs paid)
      - Progress bar
    - **Card 3**: Llama 32B
      - Display: "1/1 uses" or "10/10 uses"
      - Progress bar
    - **Note**: "Usage resets on [DATE]"
- **Start Chatting Button**:
  - Large button linking to /chat

**Page 3: Chat** (`/chat`)
- Require valid JWT
- **Layout**:
  - Left sidebar (optional):
    - "New Chat" button
    - Previous conversations (if saved)
  - Main chat area:
    - Message history (chat bubbles)
      - User messages: right-aligned, blue background
      - AI messages: left-aligned, gray background
      - Show timestamp and model name under each AI response
  - Bottom input area:
    - Model selector dropdown (shows remaining uses for each)
    - Text input box (placeholder: "Type your message...")
    - "Send" button (disable if no message or out of uses)
    - Show "out of uses" message if limit reached
  - **Error handling**:
    - If Ollama offline: show "Service unavailable" message
    - If API error: show user-friendly error
    - If token expired: redirect to login with message
- **Loading state**:
  - Show "AI is thinking..." while waiting for response
  - Disable send button
  - Show loading spinner

**Page 4: Settings** (`/settings`)
- **Account Settings**:
  - Username (read-only display)
  - Email (read-only display)
  - "Change Password" button
  - "Delete Account" button (with confirmation)
- **Subscription Settings**:
  - Current tier display
  - If free: "Upgrade to Paid" button
  - If paid: "Manage Billing" and "Cancel Subscription" buttons
- **Preferences**:
  - Theme selector (light/dark mode)
  - Chat theme (default/compact)

#### UI/UX Requirements
- **Responsive Design**: Works on desktop, tablet, mobile
- **Color Scheme**:
  - Primary color: #007AFF (blue, Apple-style)
  - Background: #F5F5F5 (light gray) or #1C1C1E (dark)
  - Text: Dark gray on light, white on dark
  - Accent: Green for success, red for errors
- **Typography**:
  - Font: System font (SF Pro, -apple-system, sans-serif)
  - Headings: 24px, 20px, 18px
  - Body: 16px
  - Small: 14px
- **Buttons**:
  - Primary: Blue, white text, 8px rounded corners
  - Secondary: Gray, dark text, 8px rounded
  - Hover state: Darker shade
  - Disabled: Grayed out, no cursor
- **Form Inputs**:
  - 12px border-radius
  - 8px padding
  - 1px border, light gray
  - Focus: Blue border
- **Chat Bubbles**:
  - Max width: 80% of container
  - User: Right-aligned, light blue background
  - AI: Left-aligned, light gray background
  - Padding: 12px 16px
  - Border-radius: 12px
  - Timestamp below bubble, 12px gray text

#### JavaScript Functionality
- **LocalStorage Management**:
  - Store JWT token in localStorage under key `auth_token`
  - Store user info (username, tier) under key `user_info`
  - Check on page load if token exists and valid
- **API Calls**:
  - Use `fetch()` API, not jQuery
  - Always include `Authorization: Bearer {token}` header
  - Handle 401 (redirect to login), 429 (rate limit), 503 (server error)
- **Real-time Updates**:
  - After each chat message, fetch `/api/usage/remaining`
  - Update usage display dynamically
- **Form Validation**:
  - Client-side validation before sending
  - Server-side validation always required
- **Error Display**:
  - Toast notifications (top-right corner)
  - Inline form error messages
  - Clear, user-friendly language

---

### 7. DATABASE SCHEMA (SQLite)

```sql
-- Users Table
CREATE TABLE users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  tier TEXT NOT NULL DEFAULT 'free', -- 'free' or 'paid'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  stripe_customer_id TEXT,
  subscription_id TEXT,
  paid_since TIMESTAMP,
  last_login TIMESTAMP
);

-- Usage Table (tracks monthly uses per model group)
CREATE TABLE usage (
  usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  model_7b_uses INTEGER DEFAULT 0,
  model_14b_uses INTEGER DEFAULT 0,
  model_32b_uses INTEGER DEFAULT 0,
  month_start_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Messages Table (chat history)
CREATE TABLE messages (
  message_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  model_used TEXT NOT NULL, -- 'llama2_7b', 'qwen2_7b', 'llama2_14b', 'llama2_32b'
  user_message TEXT NOT NULL,
  ai_response TEXT NOT NULL,
  tokens_estimated INTEGER,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  conversation_id INTEGER,
  deleted_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Password Reset Tokens Table
CREATE TABLE password_reset_tokens (
  token_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(user_id)
);
```

---

### 8. BACKEND SETUP (Python/FastAPI)

#### Project Structure
```
chatbot-backend/
├── main.py              # FastAPI app entry point
├── config.py            # Environment variables & settings
├── database.py          # SQLite connection & operations
├── models.py            # Pydantic models for validation
├── routes/
│   ├── auth.py          # /api/auth/* endpoints
│   ├── chat.py          # /api/chat/* endpoints
│   ├── usage.py         # /api/usage/* endpoints
│   └── subscription.py  # /api/subscription/* endpoints
├── services/
│   ├── ollama_service.py    # Ollama API calls
│   ├── stripe_service.py    # Stripe API calls
│   ├── email_service.py     # Email sending (optional)
│   └── auth_service.py      # JWT & password hashing
├── middleware/
│   ├── auth.py          # JWT verification middleware
│   └── rate_limit.py    # Rate limiting
├── requirements.txt
├── .env.example
├── .env (not in git, keep secret)
└── database.db          # SQLite file
```

#### Dependencies (requirements.txt)
```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.23
bcrypt==4.1.1
pyjwt==2.8.1
requests==2.31.0
python-dotenv==1.0.0
stripe==7.4.0
python-multipart==0.0.6
aiofiles==23.2.1
cors==1.0.1
```

#### Environment Variables (.env)
```
# Database
DATABASE_URL=sqlite:///./database.db

# JWT
JWT_SECRET_KEY=your_super_secret_key_change_this_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=720  # 30 days

# Ollama
OLLAMA_BASE_URL=http://192.168.x.x:11434  # M2 Mac IP address

# Stripe
STRIPE_API_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Email (if using)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=your_app_password

# App
APP_NAME=LLM Chatbot
ENVIRONMENT=production
CORS_ORIGINS=["https://yourdomain.com", "http://localhost:3000"]
```

#### main.py (FastAPI App)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import auth, chat, usage, subscription
from config import settings

app = FastAPI(title=settings.APP_NAME)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])
app.include_router(subscription.router, prefix="/api/subscription", tags=["subscription"])

# Serve static frontend files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

### 9. DEPLOYMENT INSTRUCTIONS

#### Option A: DigitalOcean App Platform
1. Create DigitalOcean account
2. Create new App Platform project
3. Connect GitHub repo
4. Set environment variables (from .env)
5. Deploy automatically on git push
6. Enable HTTPS
7. Point custom domain

#### Option B: DigitalOcean Droplet (VPS)
1. Create Ubuntu 22.04 droplet ($6/month)
2. SSH into droplet
3. Install Python, pip, git
4. Clone repo: `git clone [your-repo]`
5. Install deps: `pip install -r requirements.txt`
6. Run app: `python main.py` (or use gunicorn for production)
7. Use Nginx as reverse proxy
8. Set up SSL with Let's Encrypt
9. Point domain to droplet IP

#### Option C: Heroku (simplest)
1. Create Heroku account
2. Create new app
3. Connect GitHub
4. Set config vars (environment variables)
5. Deploy
6. Heroku Postgres for database (optional, SQLite works fine too)

#### Setup Ollama on M2 Mac Air
1. Download Ollama from https://ollama.ai
2. Install and open app
3. Pull models:
   ```bash
   ollama pull llama2:7b
   ollama pull qwen2:7b
   ollama pull llama2:14b
   ollama pull llama2:32b
   ```
4. Start Ollama server: `ollama serve` (runs on localhost:11434)
5. Get M2's local IP: `ifconfig | grep "inet "` (something like 192.168.x.x)
6. Update .env with: `OLLAMA_BASE_URL=http://192.168.x.x:11434`
7. Keep M2 on and Ollama running 24/7 (consider auto-start on boot)

#### Domain Setup
1. Buy domain (Namecheap, GoDaddy, etc.)
2. Point nameservers to hosting provider's nameservers
3. Create DNS records:
   - A record: @ → your server IP
   - CNAME: www → your domain
4. Enable SSL (automatic with Let's Encrypt)

---

### 10. SECURITY CHECKLIST

- [ ] Passwords hashed with bcrypt (salt rounds 12)
- [ ] JWT tokens expire in 30 days
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] CORS configured to only allow your domain
- [ ] Rate limiting: max 1 request per 2 seconds per user
- [ ] Stripe API key kept in .env, never in code/frontend
- [ ] Database queries use parameterized queries (prevent SQL injection)
- [ ] User input validated server-side
- [ ] Stripe webhooks verified with signature
- [ ] No sensitive data (passwords, keys) logged
- [ ] Ollama API call timeout: 60 seconds
- [ ] User messages not stored longer than necessary (optional deletion)

---

### 11. ERROR HANDLING & RESPONSES

#### Standard Response Format (Success)
```json
{
  "status": "success",
  "data": { /* specific data */ }
}
```

#### Standard Response Format (Error)
```json
{
  "status": "error",
  "error_code": "string (e.g., 'INVALID_PASSWORD')",
  "message": "User-friendly error message",
  "details": { /* optional technical details */ }
}
```

#### HTTP Status Codes
- 200 OK: Success
- 201 Created: Resource created
- 400 Bad Request: Validation error
- 401 Unauthorized: Invalid/missing token
- 403 Forbidden: User not allowed
- 404 Not Found: Resource doesn't exist
- 409 Conflict: Duplicate username/email
- 429 Too Many Requests: Rate limit hit or out of uses
- 500 Internal Server Error: Server error
- 503 Service Unavailable: Ollama offline

---

### 12. TESTING REQUIREMENTS

#### Unit Tests
- Test password hashing (bcrypt works correctly)
- Test JWT generation/validation
- Test usage calculation logic
- Test tier-based limit logic

#### Integration Tests
- Test signup → login → chat flow
- Test usage limits (free user hits 100, can't send more)
- Test tier upgrade (free → paid)
- Test Ollama integration (mock Ollama API)
- Test Stripe webhook handling

#### Manual Testing
- Try signing up with invalid password (should fail)
- Try logging in with wrong password (should fail)
- Send 100 messages with free tier (11th should fail)
- Subscribe to paid tier, verify unlimited 7B
- Test chat with all 4 models
- Test on mobile browser (responsive design)

---

### 13. MONITORING & MAINTENANCE

#### Logs to Track
- Failed login attempts
- API errors
- Ollama downtime
- Stripe webhook failures
- User signup rate

#### Backup Strategy
- Database.db: backup daily to cloud (AWS S3, DigitalOcean Spaces)
- User messages: consider 30-day auto-delete for privacy

#### Future Enhancements
- Email notifications (new features, billing)
- User referral program
- Model-specific pricing (14B/32B cost extra?)
- Conversation saving/naming
- API for third-party integrations
- Analytics dashboard (revenue, user count, model popularity)
- Support tickets/help system

---

## IMPLEMENTATION PRIORITY (MVP FIRST)

### Phase 1: MVP (1-2 weeks)
✅ User auth (signup/login)
✅ Ollama integration (7B models only)
✅ Simple chat interface
✅ Free tier with 100 uses/month limit
✅ Basic dashboard showing remaining uses
❌ No payments yet (all users free)

### Phase 2: Add Larger Models (1 week)
✅ Integrate 14B and 32B models
✅ Separate usage tracking per model
✅ Model selector on chat page

### Phase 3: Payment System (1 week)
✅ Stripe integration
✅ Paid tier ($19/month)
✅ Upgrade button on dashboard
✅ Usage limits per tier

### Phase 4: Polish (1 week)
✅ Better UI/UX
✅ Mobile responsiveness
✅ Email notifications
✅ Password reset
✅ Account deletion

### Phase 5: Scale & Monitor (ongoing)
✅ Set up analytics
✅ Monitor Ollama performance
✅ Optimize database queries
✅ Add more models/features

---

## FINAL NOTES FOR AI ASSISTANT

When implementing:

1. **Start simple**: Get auth + one model working first
2. **Test as you build**: Don't build everything, then test
3. **Use environment variables** for all secrets (never hardcode)
4. **Handle errors gracefully**: Show user-friendly messages
5. **Rate limiting is important**: Prevent abuse and server overload
6. **Stripe is critical**: Get this right, test in sandbox mode first
7. **Ollama reliability**: Handle when M2 goes offline
8. **Database transactions**: Use transactions for payment processing
9. **JWT tokens**: Don't over-complicate, just sign with secret key
10. **Frontend is user-facing**: Make it clean and responsive

**This spec is exhaustive. You have everything you need to build this.**

Good luck! 🚀
