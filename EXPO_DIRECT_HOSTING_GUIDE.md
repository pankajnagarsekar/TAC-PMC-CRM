# TAC-PMC-CRM: Direct Expo Hosting (No App Store Required)

**Goal**: Deploy your app directly on Expo so anyone can download and use it without App Store or Play Store.

---

## 🎯 Three Deployment Options (No Store Required)

### Option 1: **Expo Web + Vercel/Netlify** (Easiest - Browser-Only)
- ✅ Zero setup, deploy in 5 minutes
- ✅ Accessible via web browser URL
- ✅ No native build needed
- ✅ Free tier available
- ❌ No native camera/location on all devices
- 📍 **Best for**: Quick MVP, collaborative testing

### Option 2: **EAS Build + Expo Go Link** (Recommended - Full Native Features)
- ✅ Access native features (camera, location, voice)
- ✅ Shareable link anyone can open
- ✅ iOS & Android support
- ✅ Auto-updating (with Expo Updates)
- ✅ No App Store submission needed
- 💰 Free tier: 30 builds/month
- 📍 **Best for**: Full production app without store friction

### Option 3: **Self-Hosted Expo Server** (Advanced - Complete Control)
- ✅ Full control over hosting
- ✅ Can run on your own servers
- ✅ Air-gapped/private deployments possible
- ❌ More infrastructure work
- 📍 **Best for**: Enterprise/private deployments

---

## 🚀 RECOMMENDED: Option 2 - EAS Build + Expo Updates

This gives you a **shareable link** that users can install directly from any device.

### Step 1: Create Expo Account

```bash
# Go to https://expo.dev and create free account
# You'll get username: [YOUR_USERNAME]
```

### Step 2: Install EAS CLI

```bash
npm install -g eas-cli

# Or if you prefer:
npx eas-cli@latest
```

### Step 3: Login to Expo

```bash
eas login
# Enter your Expo credentials
# Verify: eas whoami
```

### Step 4: Initialize EAS in Your Project

```bash
cd apps/mobile
eas init

# This will:
# - Create eas.json if needed
# - Add your Expo project ID
# - Ask about your project
```

### Step 5: Update eas.json for Production

```bash
# Edit eas.json to look like this:
```

```json
{
  "cli": { "version": ">= 14.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "env": {
        "EXPO_PUBLIC_BACKEND_URL": "https://your-production-api.com"
      }
    },
    "production": {
      "distribution": "store",
      "env": {
        "EXPO_PUBLIC_BACKEND_URL": "https://your-production-api.com"
      }
    }
  },
  "submit": {
    "production": {}
  }
}
```

### Step 6: Update Backend URL for Production

```bash
# Edit .env in apps/mobile/
EXPO_PUBLIC_BACKEND_URL=https://your-production-api-url.com

# Example: if your API is on Render
EXPO_PUBLIC_BACKEND_URL=https://tac-pmc-api.onrender.com
```

### Step 7: Build for Android

```bash
cd apps/mobile

# First time: more time (5-15 minutes)
eas build --platform android

# You'll see options:
# APK (recommended for direct installation)
# AAB (for Play Store - skip this)

# Choose: APK - share link
```

**Output**: You get a shareable APK download link! Anyone can:
1. Click link on Android device
2. Install APK directly
3. App opens and works

### Step 8: Build for iOS

```bash
cd apps/mobile

# First time: even longer (10-20 minutes)
eas build --platform ios

# You'll see options:
# Ad Hoc (for direct installation via TestFlight)
# Choose: Ad Hoc

# Output: Invite link via TestFlight
```

**Output**: Share TestFlight link with iOS users

### Step 9: Enable Auto-Updates (Optional but Recommended)

```bash
# Install expo-updates
npx expo install expo-updates

# This allows you to push updates WITHOUT rebuilding:
# - UI changes
# - Bug fixes
# - New features

# Later, to publish updates:
eas update --platform android
eas update --platform ios
```

---

## 📱 Sharing Your App

### Android Users
```
1. Send them this link: [Your APK download link from Step 7]
2. They tap "Install"
3. App opens and works immediately
```

### iOS Users
```
1. Send them TestFlight invite link
2. They install iOS app
3. App works immediately
```

### Web Users
```
1. Send them: https://your-app.vercel.app
2. They open in browser
3. Works like native app (PWA)
```

---

## 🔄 Updating Your App (After Launch)

### Small Updates (UI, Bug Fixes)
No rebuild needed! Just update and publish:

```bash
cd apps/mobile

# Make your changes
# ... edit code ...

# Publish update
eas update --platform android --platform ios

# Users get update next time they open app
```

### Major Updates (New Permissions, Native Changes)
Need to rebuild:

```bash
cd apps/mobile

# Update code
# ... edit code ...

# Rebuild
eas build --platform android
eas build --platform ios

# Share new links with users
```

---

## 💰 Cost Breakdown

### Free Tier (Expo)
- ✅ 30 builds/month
- ✅ Unlimited updates
- ✅ Web hosting (basic)
- ✅ Perfect for MVP/testing

### Paid Tier
- 💰 $348/year (Priority builds, more builds/month)
- Not needed for MVP

### Infrastructure Costs
If using production API (Render, AWS, etc):
- Render.com: Free tier available
- AWS: Pay per usage
- Your own server: Your cost

---

## 🎯 Complete Workflow

### First Launch
```bash
# 1. Create Expo account
# 2. eas login
# 3. cd apps/mobile
# 4. eas init
# 5. eas build --platform android
# 6. eas build --platform ios
# 7. Share links with users
```

### After Launch (Publishing Updates)
```bash
# Small fixes:
eas update --platform android --platform ios

# Major changes:
eas build --platform android
eas build --platform ios
```

---

## 📊 Comparison: Your Options

| Feature | Expo Web | EAS Build (APK/TestFlight) | Self-Hosted |
|---------|----------|---------------------------|-------------|
| **Setup Time** | 5 min | 30 min | 1+ hour |
| **Browser Access** | ✅ Yes | ❌ No | ✅ Yes |
| **Native Features** | ⚠️ Limited | ✅ Full | ✅ Full |
| **Android Support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **iOS Support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Hosting Cost** | $0-10/mo | $0 (free tier) | $5-100+/mo |
| **Build Time** | N/A | 5-20 min | 5-20 min |
| **Update Frequency** | Manual | Instant (hot update) | Custom |
| **User Installation** | Link click | APK download/TestFlight | Link click |
| **Best For** | MVP testing | Production launch | Enterprise |

---

## 🔐 Security Notes

Before launching production:

1. **Update Backend URL**
   ```bash
   # .env should have production API:
   EXPO_PUBLIC_BACKEND_URL=https://your-production-api.com
   ```

2. **Enable HTTPS**
   ```bash
   # Your backend should be HTTPS only
   # Expo apps require secure connections
   ```

3. **Validate Credentials**
   ```bash
   # Users will login with real credentials
   # Ensure auth is secure on backend
   ```

4. **Privacy Policy**
   - Create privacy policy for your app
   - Users need to know what data is collected

5. **Terms of Service**
   - Create basic terms for app usage

---

## 📋 Pre-Launch Checklist

- [ ] Expo account created
- [ ] EAS CLI installed
- [ ] `eas login` successful
- [ ] `eas init` completed
- [ ] .env updated with production API URL
- [ ] eas.json configured
- [ ] Backend API running on production URL
- [ ] Android build successful
- [ ] iOS build successful
- [ ] Downloaded test apps and verified they work
- [ ] Created simple privacy policy
- [ ] Tested with test user account
- [ ] Camera permissions tested
- [ ] Location permissions tested
- [ ] Shared links with beta testers

---

## 🎯 Next Steps (Right Now)

### 1. Create Expo Account (2 minutes)
```bash
# Visit https://expo.dev
# Sign up (free)
# Write down your username
```

### 2. Install EAS CLI (1 minute)
```bash
npm install -g eas-cli
```

### 3. Login (1 minute)
```bash
eas login
# Enter credentials
```

### 4. Initialize (2 minutes)
```bash
cd apps/mobile
eas init
```

### 5. Build Android (15 minutes)
```bash
eas build --platform android
# Wait for build to complete
# Copy APK download link
```

### 6. Share Link!
```bash
# Send link to Android users
# They can install immediately
```

**Total time: ~25 minutes to first shareable build!**

---

## 🆘 Troubleshooting

### "Build failed"
```bash
# Check if backend URL is correct:
cat apps/mobile/.env | grep EXPO_PUBLIC_BACKEND_URL

# Rebuild:
eas build --platform android --clean
```

### "Cannot connect to backend"
```bash
# Verify backend is online:
curl https://your-api.com

# Update .env:
EXPO_PUBLIC_BACKEND_URL=https://your-api.com

# Rebuild with clean:
eas build --platform android --clean
```

### "eas login failed"
```bash
# Check if credentials are correct:
eas logout
eas login
```

### "iOS build stuck"
```bash
# Check status:
eas build:list --platform ios

# Cancel and retry:
eas build:cancel
eas build --platform ios --clean
```

---

## 📚 Resources

- **Expo Docs**: https://docs.expo.dev
- **EAS Build Docs**: https://docs.expo.dev/build/introduction/
- **EAS Updates**: https://docs.expo.dev/eas-update/introduction/
- **TestFlight (iOS)**: https://testflight.apple.com
- **Your Project**: See CLAUDE.md for backend setup

---

## ✅ You Now Have

- ✅ Shareable APK link for Android users
- ✅ TestFlight link for iOS users
- ✅ Ability to push updates without rebuilding
- ✅ Free hosting via Expo
- ✅ Production-ready app live online

**Congratulations! Your app is now live!** 🎉
