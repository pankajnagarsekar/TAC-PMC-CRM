import { Redirect } from 'expo-router';

export default function AttendanceRedirect() {
  return <Redirect href="/(admin)/attendance-view" />;
}
