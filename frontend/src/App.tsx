import axios from 'axios';
import { useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import './App.scss';
import NavBar from './components/NavBar';
import AboutPage from './pages/AboutPage';
import DemosPage from './pages/DemosPage';
import HomePage from './pages/HomePage';

axios.defaults.responseType = 'blob';
axios.defaults.headers.common['Content-Type'] = 'multipart/form-data';

const App: React.FC = () => {
  const [background, setBackground] = useState<number>(15);

  useEffect(() => {
    let direction = 1;
    const intervalId = setInterval(() => {
      setBackground((background) => {
        const newBackground = background + direction;
        if (newBackground === 15 || newBackground === 70) {
          direction *= -1;
        }
        return newBackground;
      });
    }, 500);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    document.documentElement.style.backgroundColor = `rgb(151, ${background}, ${background})`;
  }, [background]);

  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path='/' element={<HomePage />} />
        <Route path='/about' element={<AboutPage />} />
        <Route path='/demos' element={<DemosPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
