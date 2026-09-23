import { AppRegistry } from 'react-native';
import { createRoot } from 'react-dom/client';
import App from './App';
AppRegistry.registerComponent('ProjectedAICamera', () => App);
createRoot(document.getElementById('root')!).render(<App />);
