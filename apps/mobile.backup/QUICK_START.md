# TAC-PMC-CRM Mobile: Quick Start 🚀

## Pre-Launch Checklist ✅

### 1. Verify Backend is Running
```bash
# From project root
cd apps/api
npm run dev
# Should see: "Application startup complete" at http://localhost:8000
```

### 2. Configure Environment
```bash
# Mobile app .env is already configured for local development
# For testing: uses Android emulator loopback (10.0.2.2:8000)
# For production: update EXPO_PUBLIC_BACKEND_URL in .env
```

### 3. Install Dependencies (if not already done)
```bash
cd apps/mobile
npm install
```

---

## 🎯 Launch in 30 Seconds

### **Option A: Web (Easiest - Recommended for Quick Testing)**
```bash
cd apps/mobile
npm run dev
# Opens http://localhost:3001 automatically
# ✅ Full app functionality on desktop browser
# ✅ Can test camera via device camera API
# ✅ Can test geolocation
```

### **Option B: iOS Simulator**
```bash
cd apps/mobile
npm run ios
# Requires: Xcode + iOS simulator installed
# Opens app in iPhone simulator
```

### **Option C: Android Emulator**
```bash
cd apps/mobile
npm run android
# Requires: Android Studio + emulator running
# Opens app in Android emulator
```

### **Option D: Physical Device (Best for Real Testing)**
```bash
cd apps/mobile
npm start
# Scans QR code with "Expo Go" app on your phone
# Most realistic testing experience
```

---

## 🔍 Verify App is Working

### Check These Screens:

1. **Login Screen** (`login.tsx`)
   - Should load without errors
   - Try test credentials

2. **Dashboard** (role-based)
   - Admin: Full dashboard access
   - Supervisor: DPR & attendance view
   - Client: Reports only

3. **Camera Feature** (Admin/Supervisor)
   - Open any photo capture field
   - Take a test photo
   - Verify upload works

4. **Location Feature**
   - Should request location permission
   - Shows current position (web: uses browser location)

---

## 📊 Testing Features

### Authentication
```
Test User Credentials (from seed data):
- Admin: admin@example.com / password123
- Supervisor: supervisor@example.com / password123
- Client: client@example.com / password123
```

### Mobile-Specific Features
- ✅ Camera capture (for DPR photos)
- ✅ Location tracking (site verification)
- ✅ Voice recording (supervisor voice logs)
- ✅ Offline support (async storage)
- ✅ Dark mode (theme switching)
- ✅ Role-based navigation
- ✅ Responsive layout

---

## 🐛 Troubleshooting

### App won't start
```bash
rm -rf node_modules
npm install
npm run dev
```

### Backend connection error
- Verify backend is running: `curl http://localhost:8000/docs`
- Check `.env` has correct `EXPO_PUBLIC_BACKEND_URL`
- For Android emulator: URL should be `http://10.0.2.2:8000`
- For physical device: URL should be your machine's LAN IP (e.g., `http://192.168.1.100:8000`)

### Port 3001 already in use
```bash
lsof -i :3001
kill -9 <PID>
npm run dev
```

### Dependencies issue
```bash
npm ci  # Clean install
npm run dev
```

---

## 🌐 For Production Deployment

See full guide: `../EXPO_LAUNCH_GUIDE.md`

Quick command:
```bash
# Build for App Store / Play Store
eas build --platform ios
eas build --platform android

# Or build locally
npm run build  # Creates optimized web build
```

---

## 📱 Next Steps

1. ✅ Launch the app locally
2. ✅ Test authentication & navigation
3. ✅ Test mobile features (camera, location)
4. ✅ Review code with Superpowers workflow
5. ✅ Submit to app stores (when ready)

**Happy testing!** 🎉
