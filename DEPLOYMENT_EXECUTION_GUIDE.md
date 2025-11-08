# 🚀 AI Education Platform - Railway Deployment Execution

## 📋 Current Status
- ✅ Railway CLI installed and authenticated (3270930076@qq.com)
- ✅ Railway dashboard opened (https://railway.app/new)
- ✅ Backend configuration files ready
- ✅ Frontend environment setup complete

## 🎯 Step-by-Step Deployment (Following DEPLOYMENT_GUIDE.md)

### Phase 1: Backend Deployment

#### Step 1: Create Project via GitHub Import
**🌐 In the Railway Dashboard (should be open):**

1. Click **"Deploy from GitHub repo"**
2. Select repository: `aiguru` or connect your GitHub account
3. **Important**: Set **Root Directory** to: `backend`
4. Click **"Deploy"**

#### Step 2: Add Database Services
**After backend deployment starts:**

1. In your Railway project dashboard, click **"New Service"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Wait for PostgreSQL to initialize
4. Click **"New Service"** again
5. Select **"Database"** → **"Add Redis"**

#### Step 3: Configure Environment Variables
**Go to your backend service → "Variables" tab:**

**Basic Configuration:**
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

**Security Configuration (Required):**
```bash
SECRET_KEY=aiguru-super-secret-key-for-production-deployment-32chars
JWT_SECRET_KEY=aiguru-jwt-secret-key-for-production-deployment-32chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

**AI Service Configuration (Required):**
```bash
OPENROUTER_API_KEY=your-openrouter-api-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=google/gemini-2.0-flash-exp:free
```

**CORS and Security:**
```bash
CORS_ORIGINS=*
ALLOWED_HOSTS=*
```

**Cost Optimization:**
```bash
ENABLE_UNIFIED_AGENT=true
ENABLE_SMART_CACHE=true
CACHE_SIMILARITY_THRESHOLD=0.85
DEFAULT_GRADING_MODE=fast
```

**LLM Configuration:**
```bash
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000
```

#### Step 4: Get OpenRouter API Key
1. Visit: https://openrouter.ai/keys
2. Create account (free tier available)
3. Generate API key
4. Add to Railway as `OPENROUTER_API_KEY`

### Phase 2: Frontend Deployment

#### Option A: Vercel Deployment (Recommended)
1. **Visit**: https://vercel.com/new
2. **Import GitHub repository**
3. **Framework Preset**: Next.js
4. **Root Directory**: `frontend`
5. **Environment Variables**:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NEXT_PUBLIC_APP_NAME=AI Education Platform
   ```

#### Option B: Railway Deployment
1. **In same Railway project**, click **"New Service"**
2. **Select**: "GitHub Repo"
3. **Root Directory**: `frontend`
4. **Environment Variables**:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```

### Phase 3: Verification and Testing

#### Backend Health Check
```bash
curl https://your-backend.railway.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "ai-education-backend",
  "version": "0.1.0"
}
```

#### API Documentation
Visit: `https://your-backend.railway.app/docs`

#### Database Connection Test
```bash
railway connect postgresql
\dt  # List tables
```

## 🔧 CLI Commands (After Web Deployment)

If you want to link your local CLI to the deployed project:

```bash
# List your projects to find the project ID
railway list

# Link to the project
railway link your-project-id

# View project status
railway status

# View logs
railway logs

# Set additional variables via CLI
railway variables set KEY=value
```

## 📊 Environment Variables Reference

### Required Variables
| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | Application environment |
| `SECRET_KEY` | 32+ char string | Application security key |
| `JWT_SECRET_KEY` | 32+ char string | JWT signing key |
| `OPENROUTER_API_KEY` | `sk-or-v1-xxx` | AI service API key |

### Auto-Generated Variables
| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | PostgreSQL service | Database connection |
| `REDIS_URL` | Redis service | Cache connection |

## 🎯 Deployment Checklist

### Backend Deployment
- [ ] Railway project created via GitHub import
- [ ] Root directory set to `backend`
- [ ] PostgreSQL service added
- [ ] Redis service added
- [ ] All environment variables configured
- [ ] OpenRouter API key obtained and set
- [ ] Deployment completed successfully

### Frontend Deployment
- [ ] Vercel/Railway project created
- [ ] Root directory set to `frontend`
- [ ] `NEXT_PUBLIC_API_URL` configured with backend URL
- [ ] Build and deployment successful

### Verification
- [ ] Backend health endpoint responds
- [ ] API documentation accessible
- [ ] Frontend loads and connects to backend
- [ ] Database services running
- [ ] Test AI grading request works

## 🆘 Troubleshooting

### Common Issues

1. **Build Failures**
   - Check root directory is set correctly
   - Verify requirements.txt exists in backend
   - Check package.json exists in frontend

2. **Environment Variable Issues**
   - Ensure all required variables are set
   - Check for typos in variable names
   - Verify API key format

3. **Database Connection Errors**
   - Wait for services to fully initialize
   - Check Railway dashboard for service status
   - Verify DATABASE_URL is auto-generated

4. **CORS Errors**
   - Set CORS_ORIGINS to include frontend domain
   - Use `*` for development/testing

## 💰 Cost Estimate

| Service | Provider | Monthly Cost |
|---------|----------|--------------|
| Backend + Databases | Railway | ~$5-10 |
| Frontend | Vercel | Free |
| AI API | OpenRouter | ~$0.009/grading |
| **Total** | | **~$5-15/month** |

## 🎉 Success Indicators

Your deployment is successful when:
- ✅ Backend health check returns "healthy"
- ✅ API docs load at `/docs`
- ✅ Frontend displays without errors
- ✅ All services show "Running" in Railway
- ✅ Test grading request completes

## 📞 Next Steps After Deployment

1. **Test Core Functionality**
   - Upload sample image
   - Test AI grading
   - Verify coordinate annotations

2. **Optional Configurations**
   - Set up custom domain
   - Configure Firebase Auth
   - Add monitoring alerts

3. **Production Readiness**
   - Review security settings
   - Set up backups
   - Monitor performance

---

**Railway Dashboard**: The deployment process starts with the Railway dashboard that should be open in your browser. Follow the steps above for a successful deployment! 🚀