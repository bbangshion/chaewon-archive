import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#100D15',
        surface: '#18131F',
        raised: '#251B2D',
        line: '#423349',
        paper: '#F7F2FA',
        ash: '#B3A6B9',
        blush: '#C7A3DF',
        violet: '#C7A3DF',
      },
      fontFamily: {
        sans: ['Inter', 'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        ambient: '0 14px 44px rgba(0,0,0,.19)',
      },
      transitionTimingFunction: {
        plush: 'cubic-bezier(0.25, 1, 0.5, 1)',
      },
    },
  },
  plugins: [],
} satisfies Config;
