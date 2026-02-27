// INDEX - ENTRY POINT
// Redirects based on auth context and role

import { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';

const PRIMARY = '#171717';

export default function Index() {
  const router = useRouter();
  const { isLoading, isAuthenticated, user } = useAuth();

  useEffect(() => {
    if (isLoading) {
      return;
    }

    if (!isAuthenticated || !user?.role) {
      router.replace('/login');
      return;
    }

    if (user.role === 'Admin') {
      router.replace('/(admin)/dashboard');
    } else if (user.role === 'Supervisor') {
      router.replace('/(supervisor)/dashboard');
    } else {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, user, router]);

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
