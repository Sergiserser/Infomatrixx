import { StepPrepDesktop } from './components';
import { Toaster } from 'sonner';

export default function App() {
  return (
    <>
      <StepPrepDesktop />
      <Toaster position="top-center" richColors />
    </>
  );
}