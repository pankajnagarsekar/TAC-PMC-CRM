import React, { useEffect } from 'react';
import { Stack, useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';

export default function ClientLayout() {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace('/login'); return;
      } else if (user?.role !== 'Client') {
        // If not a client, send back to home which handles routing
        router.replace('/');
      }
    }
  }, [isAuthenticated, isLoading, user, router]);

  // Guard: render nothing while auth is resolving
  if (isLoading) return null;

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="dashboard" />
    </Stack>
  );
}
