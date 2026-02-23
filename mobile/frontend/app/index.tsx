// INDEX - ENTRY POINT
// Check SecureStore for token and redirect based on role

import { useEffect, useState } from 'react';
import { View, ActivityIndicator, StyleSheet, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';

const PRIMARY = '#1E3A5F';

export default function Index() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    checkAuthAndRedirect();
  }, []);

  const checkAuthAndRedirect = async () => {
    try {
      let token: string | null = null;
      let role: string | null = null;

      if (Platform.OS === 'web') {
        // Web: use localStorage
        token = localStorage.getItem('access_token');
        role = localStorage.getItem('user_role');
      } else {
        // Native: use SecureStore
        token = await SecureStore.getItemAsync('access_token');
        role = await SecureStore.getItemAsync('user_role');
      }

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
