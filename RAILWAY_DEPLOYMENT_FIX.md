# 🔧 Railway Deployment - GitHub Connection Fix

## ❌ **Issue Identified**
- Repository name: `ZkwareDAO/aiguru` (not just `aiguru`)
- Missing GitHub connection options
- No root directory selection

## ✅ **Solution: Corrected Deployment Steps**

### **Method 1: Use Correct Railway Interface**

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Click "New Project"** (not "Deploy from GitHub repo")
3. **Select "Deploy from GitHub repo"**
4. **If GitHub not connected:**
   - Click "Connect GitHub Account"
   - Authorize Railway to access your repositories
   - Select repositories you want to give Railway access to

### **Method 2: Direct Repository URL**

1. **Repository URL**: `https://github.com/ZkwareDAO/aiguru`
2. **In Railway Dashboard:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Look for `ZkwareDAO/aiguru` in the list
   - **Set Root Directory**: `new_aicorrection/backend`

### **Method 3: CLI Deployment (Alternative)**

```bash
# Navigate to backend directory
cd backend

# Initialize Railway project
railway login
railway init

# Deploy current directory
railway up
```

## 🎯 **Correct Configuration**

### **Repository Details:**
- **Owner**: ZkwareDAO
- **Repository**: aiguru
- **Root Directory**: `new_aicorrection/backend`
- **Branch**: main

### **Service Configuration:**
- **Framework**: Python/FastAPI
- **Build Command**: Auto-detected (nixpacks)
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 📋 **Step-by-Step Fix**

### **1. Open Railway Dashboard**
```
https://railway.app/dashboard
```

### **2. Create New Project**
- Click "New Project"
- Select "Deploy from GitHub repo"

### **3. Connect GitHub (if needed)**
- Click "Connect GitHub Account"
- Authorize Railway
- Grant access to `ZkwareDAO/aiguru`

### **4. Select Repository**
- Find `ZkwareDAO/aiguru` in the list
- Click on it

### **5. Configure Deployment**
- **Root Directory**: `new_aicorrection/backend`
- **Environment**: Production
- Click "Deploy"

### **6. Add Services After Deployment**
- Add PostgreSQL service
- Add Redis service
- Configure environment variables

## 🆘 **If GitHub Connection Still Missing**

### **Alternative: Use Railway CLI**

```bash
# From your backend directory
cd C:\Users\lixiaomin\aiguru\new_aicorrection\backend

# Login and create project
railway login
railway init --name ai-education-backend

# Add services
railway add postgresql
railway add redis

# Set environment variables
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set SECRET_KEY=7g608QhbIm9irZ_zo8n219PRiY6ldm5WoHrL-OaR9tA
railway variables set JWT_SECRET_KEY=ldFtOUlsLF7KN3-LHYduTo5rGgVJVzHAKLnX9BQvQmI
railway variables set OPENROUTER_API_KEY=your-openrouter-key-here

# Deploy
railway up
```

## 💡 **Important Notes**

1. **Repository Path**: Your repo is `ZkwareDAO/aiguru`, not just `aiguru`
2. **Root Directory**: Must be set to `new_aicorrection/backend`
3. **GitHub Access**: Railway needs permission to access your repositories
4. **Configuration Files**: Already pushed to GitHub ✅

## 🎯 **Next Steps**

1. **Try Method 1** with correct repository name
2. **If GitHub connection issues persist**, use CLI method
3. **After successful deployment**, add database services
4. **Configure environment variables** from RAILWAY_DEPLOYMENT_CONFIG.md

Your repository is now updated with all deployment configurations. The issue is just the GitHub connection and using the correct repository name!