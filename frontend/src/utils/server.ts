import { AxiosResponse } from 'axios';
import JSZip from 'jszip';

export const fileToArrayBuffer = async (file: File): Promise<ArrayBuffer> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
};

export const promptDownload = (url: string, name: string): void => {
  const a = document.createElement('a');
  a.href = url;
  a.download = `${name}`;
  a.click();
};

export const extractFilesFromZip = async (
  res: AxiosResponse
): Promise<File[]> => {
  const zip = await JSZip.loadAsync(res.data);
  const files: File[] = [];

  for (const fileName in zip.files) {
    if (!zip.files[fileName].dir) {
      const file = zip.files[fileName];
      const blob = await file.async('blob');

      files.push(
        new File([blob], zip.files[fileName].name, {
          type: file.name.split('.').pop()!,
        })
      );
    }
  }

  return files;
};

export const zipFiles = async (files: File[]): Promise<string> => {
  const zip = new JSZip();

  files.forEach(async (file) => {
    zip.file(file.name, file.slice(0, file.size));
  });

  const blob = await zip.generateAsync({ type: 'blob' });
  return URL.createObjectURL(blob);
};
