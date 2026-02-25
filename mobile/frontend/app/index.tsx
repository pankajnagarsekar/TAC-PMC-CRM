// INDEX - ENTRY POINT
// Check SecureStore for token and redirect based on role

import { useEffect, useState } from 'react';
import { View, ActivityIndicator, StyleSheet, Platform } from 'react-native';
import { useRouter } from 'expo-router';

const PRIMARY = '#1E3A5F';

// Web-safe storage wrapper
const storage = {
  get: async (key: string): Promise<string | null> => {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    const SecureStore = require('expo-secure-store');
    return await SecureStore.getItemAsync(key);
  },
};

export default function Index() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    checkAuthAndRedirect();
  }, []);

  const checkAuthAndRedirect = async () => {
    try {
      const token = await storage.get('access_token');
      const role = await storage.get('user_role');

      if (!token) {
        // No token, redirect to login
        router.replace('/login');
        return;
      }

      // Token exists, redirect based on role
      if (role === 'Admin') {
        router.replace('/(admin)/dashboard');
      } else if (role === 'Supervisor') {
        router.replace('/(supervisor)/dashboard');
      } else {
        // Unknown role, default to login
        router.replace('/login');
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      router.replace('/login');
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={PRIMARY} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
});
