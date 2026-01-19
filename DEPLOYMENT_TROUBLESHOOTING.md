# Deployment Troubleshooting Guide

## Search Not Working After Deploy

### Common Issue: CORS Configuration

If search requests fail on Render but work locally, it's almost always a CORS configuration issue.

### Symptoms

- ✅ Works locally (`localhost:8080` → `localhost:8000`)
- ❌ Fails on Render (OPTIONS requests return 400/403)
- Browser console shows: `CORS policy: No 'Access-Control-Allow-Origin' header`

### Solution

#### Step 1: Find Your Frontend URL on Render

1. Go to Render dashboard → Your frontend service
2. Copy the service URL (e.g., `https://smartbite-mobile-ui.onrender.com`)
3. Make sure there's **no trailing slash**

#### Step 2: Update Backend CORS Environment Variable

1. Go to Render dashboard → Backend service (`nl-grocery-aggregator`)
2. Navigate to **Environment** tab
3. Find or add: `CORS_ALLOWED_ORIGINS`
4. Set value to your frontend URL(s):
   ```
   https://smartbite-mobile-ui.onrender.com
   ```
   Or multiple (comma-separated):
   ```
   https://smartbite-mobile-ui.onrender.com,https://nl-grocery-aggregator-frontend.onrender.com
   ```
5. **Save** the environment variable
6. **Redeploy** the backend service (Manual Deploy → Deploy latest commit)

#### Step 3: Verify CORS in Backend Logs

After redeploy, check backend **Logs** tab. You should see:

```
INFO: CORS allowed origins: ['https://smartbite-mobile-ui.onrender.com']
INFO: Application startup complete.
```

If you see localhost origins instead, `CORS_ALLOWED_ORIGINS` wasn't set correctly.

#### Step 4: Verify Frontend Environment Variable

1. Go to Render dashboard → Frontend service
2. Navigate to **Environment** tab (or **Build Settings** if using Static Site)
3. Find or add: `VITE_API_BASE_URL`
4. Set value to your backend URL:
   ```
   https://nl-grocery-aggregator.onrender.com
   ```
5. **Redeploy** the frontend (new build required for env vars to take effect)

#### Step 5: Test

1. Open your frontend URL in browser
2. Open browser DevTools → Network tab
3. Try searching for "melk"
4. Check the `/search` request:
   - Status should be `200 OK`
   - Request Headers should include `Origin: https://your-frontend-url.onrender.com`
   - Response Headers should include `Access-Control-Allow-Origin: https://your-frontend-url.onrender.com`

### Quick Debug Checklist

- [ ] Backend `CORS_ALLOWED_ORIGINS` set to frontend URL (no trailing slash)
- [ ] Frontend `VITE_API_BASE_URL` set to backend URL (no trailing slash)
- [ ] Backend service redeployed after env var change
- [ ] Frontend service rebuilt after env var change (static sites require rebuild)
- [ ] Backend logs show correct CORS origins
- [ ] Browser DevTools Network tab shows OPTIONS request succeeding

### Common Mistakes

❌ **Including trailing slashes**: `https://app.onrender.com/`  
✅ **Correct**: `https://app.onrender.com`

❌ **Using http instead of https**: `http://app.onrender.com`  
✅ **Correct**: `https://app.onrender.com`

❌ **Not redeploying after env var change**: Environment variables require service restart  
✅ **Correct**: Save env var → Redeploy → Check logs

❌ **Forgetting frontend rebuild**: Static sites need rebuild for `VITE_*` vars  
✅ **Correct**: Set env var → Trigger new build

### Still Not Working?

1. **Check backend logs** for CORS errors or startup issues
2. **Check browser console** for exact CORS error message
3. **Check Network tab** to see what URL the frontend is calling
4. **Verify URLs match exactly** (case-sensitive, protocol matters)
