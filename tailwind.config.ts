import Color from 'color';
import type { Config } from 'tailwindcss';

const orderedSpacing = Array.from({ length: 101 }).reduce<
  Record<string, string>
>((acc, _, index) => ({ ...acc, [index]: `${index}px` }), {});

const RATIO = 0.4;
const darken = (color: string, ratio = RATIO) =>
  Color(color).darken(ratio).hex();
const lighten = (color: string, ratio = RATIO) =>
  Color(color).lighten(ratio).hex();

const fontSize = {
  h0: [
    '100px',
    {
      fontWeight: '700',
      lineHeight: '120px',
    },
  ],
  h1: [
    '80px',
    {
      fontWeight: '700',
      lineHeight: '96px',
    },
  ],
  h2: [
    '56px',
    {
      fontWeight: '700',
      lineHeight: '84px',
    },
  ],
  h3: [
    '40px',
    {
      fontWeight: '700',
      lineHeight: '60px',
    },
  ],
  h4: [
    '32px',
    {
      fontWeight: '700',
      lineHeight: '48px',
    },
  ],
  h5: [
    '24px',
    {
      fontWeight: '600',
      lineHeight: '36px',
    },
  ],
  h6: [
    '18px',
    {
      fontWeight: '600',
      lineHeight: '27px',
    },
  ],
  headline: [
    '17px',
    {
      fontWeight: '700',
      lineHeight: '22px',
    },
  ],
  body: [
    '16px',
    {
      lineHeight: '24px',
    },
  ],
  'body-medium': [
    '14px',
    {
      lineHeight: '20px',
    },
  ],
  'body-small': [
    '12px',
    {
      lineHeight: '16px',
    },
  ],
  footnote: [
    '13px',
    {
      lineHeight: '18px',
    },
  ],
  'footnote-large': [
    '14px',
    {
      lineHeight: '18px',
    },
  ],
  caption: [
    '12px',
    {
      lineHeight: '16px',
    },
  ],
  'caption-2': [
    '10px',
    {
      lineHeight: '16px',
    },
  ],
  'caption-3': [
    '10px',
    {
      lineHeight: '12px',
    },
  ],
  button: [
    '16px',
    {
      fontWeight: '600',
      lineHeight: '24px',
    },
  ],
};

export default {
  /**
   * The `content` section is where you configure the paths
   * to all of your React components, and any other source files
   * that contain Tailwind class names
   */
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      fontSize: orderedSpacing,
      lineHeight: orderedSpacing,

      colors: {
        /**
         * Grayscale
         */
        black: '#141619',
        'neural-06': '#2F3138',
        'neural-05': '#454750',
        'neural-04': '#71717B',
        'neural-03': '#BBBBC1',
        'neural-02': '#E1E1E5',
        'neural-01': '#F1F1F3',
        white: '#ffffff',

        /**
         * System
         */
        error: '#EB404E',
        'error-dark': '#C02F2F',
        'error-light': '#FF8888',
        'error-subtle': '#FFECEC',
        warning: '#FFCC00',
        'warning-dark': '#897E43',
        'warning-light': '#FDDD48',
        'warning-subtle': '#F9F5DD',
        success: '#42BA94',
        'success-dark': '#259471',
        'success-light': '#AAF4CF',
        'success-subtle': '#D4ECE5',

        /**
         * Palette
         */
        primary: '#5F5FC4',
        'primary-dark': '#2B2B7F',
        'primary-medium': '#4141AB',
        'primary-light': '#8D8DEB',
        'primary-subtle': '#D4D4EC',
        rebecca: '#131A39',
        'rebecca-dark': '#141519',
        secondary: '#85D3D6',
        'secondary-dark': '#4FAFB2',
        'secondary-light': '#A8EBED',
        'secondary-subtle': '#DAF1F2',
        stroke: '#EAEAEA',
        background: '#F1F1F3',
      },

      fontWeight: {
        200: '200',
        300: '300',
        400: '400',
        500: '500',
        600: '600',
        700: '700',
        800: '800',
        900: '900',
      },

      borderRadius: {
        theme: '5px',
        'theme-lg': '10px',
      },

      keyframes: {
        'modal-in': {
          from: { opacity: '0', transform: 'translate(-50%, -55%)' },
          to: { opacity: '1', transform: 'translate(-50%, -50%)' },
        },
        'modal-out': {
          from: { opacity: '1', transform: 'translate(-50%, -50%)' },
          to: { opacity: '0', transform: 'translate(-50%, -55%)' },
        },
      },
      animation: {
        'modal-in': 'modal-in 300ms ease-out',
        'modal-out': 'modal-out 300ms ease-in',
      },
      backgroundSize: {
        'size-200': '200% 200%',
      },
      backgroundPosition: {
        'pos-0': '0% 0%',
        'pos-100': '100% 100%',
      },

      screens: {
        /**
         * High Definition Plus
         *
         * @media (min-width: 1024px and max-width: 1600px)  { ... }
         */
        hdp: { min: '1025px', max: '1600px' },

        /**
         * Desktop
         *
         * @media (min-width: 1025px { ... }
         */
        lg: { min: '1025px' },

        /**
         * High Definition
         *
         * @media (max-width: 1024px and max-width: 1366px)  { ... }
         */
        hd: { min: '1025px', max: '1366px' },

        /**
         * Desktop + Tablet
         *
         * @media (max-width: 1024px and max-width: 1366px)  { ... }
         */
        'lg-md': { min: '601px' },
        'md-lg': { min: '601px' },

        /**
         * Table + Mobile
         *
         * @media (max-width: 1024px  { ... }
         */
        'md-sm': { max: '1024px' },
        'sm-md': { max: '1024px' },

        /**
         * For tablet only
         *
         * @media (min-width: 600 and max-width: 1024px) { ... }
         */
        md: { min: '601px', max: '1024px' },

        /**
         * @media max-width: 600px  { ... }
         */
        sm: { max: '600px' },
      },

      transitionDuration: {
        DEFAULT: '300ms',
      },
    },
  },

  plugins: [],
} satisfies Config;
