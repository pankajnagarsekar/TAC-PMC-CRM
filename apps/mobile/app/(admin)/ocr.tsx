// OCR SCREEN
// Invoice scanning and data extraction

import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/ui';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

import * as ImagePicker from 'expo-image-picker';
import { ocrApi } from '../../services/apiClient';
import { OCRResult } from '../../types/api';

export default function OCRScreen() {
  const [image, setImage] = React.useState<string | null>(null);
  const [scanning, setScanning] = React.useState(false);
  const [result, setResult] = React.useState<OCRResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      alert('Permission to access gallery is required!');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.8,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      setImage(`data:image/jpeg;base64,${result.assets[0].base64}`);
      setError(null);
      setResult(null);
    }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      alert('Permission to use camera is required!');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 0.8,
      base64: true,
    });

    if (!result.canceled && result.assets[0].base64) {
      setImage(`data:image/jpeg;base64,${result.assets[0].base64}`);
      setError(null);
      setResult(null);
    }
  };

  const handleScan = async () => {
    if (!image) return;

    setScanning(true);
    setError(null);
    try {
      // Extract base64 part
      const base64Data = image.split(',')[1];
      const response = await ocrApi.scanInvoice({ image_base64: base64Data });
      setResult(response);
    } catch (err: any) {
      console.error('OCR Scan failed:', err);
      setError(err.message || 'Scanning failed');
    } finally {
      setScanning(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScrollView contentContainerStyle={styles.content}>
        <Card style={styles.headerCard}>
          <Ionicons name="scan" size={48} color={Colors.accent} />
          <Text style={styles.title}>Invoice Scanner</Text>
          <Text style={styles.subtitle}>Scan invoices to extract data automatically</Text>
        </Card>

        <Card style={styles.uploadCard}>
          {image ? (
            <View style={styles.previewContainer}>
              <TouchableOpacity onPress={pickImage} style={styles.imagePreview}>
                <Ionicons name="image" size={24} color={Colors.primary} />
                <Text style={styles.changeText}>Change Image</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={[styles.scanButton, scanning && styles.disabledButton]} 
                onPress={handleScan}
                disabled={scanning}
              >
                <Text style={styles.scanButtonText}>
                  {scanning ? 'Scanning...' : 'Start OCR Scan'}
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.buttonRow}>
              <TouchableOpacity style={styles.actionButton} onPress={takePhoto}>
                <Ionicons name="camera" size={32} color={Colors.primary} />
                <Text style={styles.actionText}>Camera</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionButton} onPress={pickImage}>
                <Ionicons name="images" size={32} color={Colors.primary} />
                <Text style={styles.actionText}>Gallery</Text>
              </TouchableOpacity>
            </View>
          )}
        </Card>

        {error && (
          <Card style={styles.errorCard}>
            <Text style={styles.errorText}>{error}</Text>
          </Card>
        )}

        <Card style={styles.resultCard}>
          <Text style={styles.resultTitle}>Extracted Data Preview</Text>
          <View style={styles.resultRow}>
            <Text style={styles.resultLabel}>Vendor Name:</Text>
            <Text style={styles.resultValue}>{result?.extracted_vendor_name || '—'}</Text>
          </View>
          <View style={styles.resultRow}>
            <Text style={styles.resultLabel}>Invoice Amount:</Text>
            <Text style={styles.resultValue}>
              {result?.extracted_amount !== undefined ? result.extracted_amount.toLocaleString() : '—'}
            </Text>
          </View>
          <View style={styles.resultRow}>
            <Text style={styles.resultLabel}>Invoice Date:</Text>
            <Text style={styles.resultValue}>{result?.extracted_date || '—'}</Text>
          </View>
          <View style={styles.resultRow}>
            <Text style={styles.resultLabel}>Invoice Number:</Text>
            <Text style={styles.resultValue}>{result?.extracted_invoice_number || '—'}</Text>
          </View>
          <View style={styles.resultRow}>
            <Text style={styles.resultLabel}>Confidence:</Text>
            <Text style={[styles.resultValue, { color: (result?.confidence_score || 0) > 0.7 ? 'green' : 'orange' }]}>
              {result?.confidence_score ? `${(result.confidence_score * 100).toFixed(0)}%` : '—'}
            </Text>
          </View>

          {result && (
            <TouchableOpacity style={styles.verifyButton}>
              <Text style={styles.verifyButtonText}>Create Payment Certificate</Text>
            </TouchableOpacity>
          )}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: Spacing.md },
  headerCard: { alignItems: 'center', padding: Spacing.xl, marginBottom: Spacing.md },
  title: { fontSize: FontSizes.xl, fontWeight: '600', color: Colors.text, marginTop: Spacing.md },
  subtitle: { fontSize: FontSizes.md, color: Colors.textSecondary, textAlign: 'center', marginTop: Spacing.xs },
  uploadCard: { marginBottom: Spacing.md, padding: Spacing.md },
  previewContainer: { alignItems: 'center' },
  imagePreview: { flexDirection: 'row', alignItems: 'center', marginBottom: Spacing.md },
  changeText: { color: Colors.primary, marginLeft: Spacing.xs, fontWeight: '500' },
  buttonRow: { flexDirection: 'row', justifyContent: 'space-around', paddingVertical: Spacing.md },
  actionButton: { alignItems: 'center' },
  actionText: { marginTop: Spacing.xs, color: Colors.textSecondary },
  scanButton: { backgroundColor: Colors.primary, paddingVertical: Spacing.md, paddingHorizontal: Spacing.xl, borderRadius: BorderRadius.md, width: '100%', alignItems: 'center' },
  scanButtonText: { color: 'white', fontWeight: '600', fontSize: FontSizes.md },
  disabledButton: { opacity: 0.6 },
  errorCard: { backgroundColor: '#FEE2E2', marginBottom: Spacing.md, padding: Spacing.md },
  errorText: { color: '#B91C1C', fontSize: FontSizes.sm, textAlign: 'center' },
  resultCard: { paddingBottom: Spacing.xl },
  resultTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text, marginBottom: Spacing.md },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: Spacing.sm, borderBottomWidth: 1, borderBottomColor: Colors.border },
  resultLabel: { fontSize: FontSizes.sm, color: Colors.textSecondary },
  resultValue: { fontSize: FontSizes.sm, fontWeight: '500', color: Colors.text },
  verifyButton: { backgroundColor: Colors.accent, marginTop: Spacing.xl, paddingVertical: Spacing.md, borderRadius: BorderRadius.md, alignItems: 'center' },
  verifyButtonText: { color: 'white', fontWeight: '700', fontSize: FontSizes.md },
});
