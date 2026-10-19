declare namespace JSX {
  interface IntrinsicElements {
    /**
     * Allow all HTML elements to accept any properties
     */
    [elemName: string]: unknown;
  }

  interface IntrinsicAttributes {
    /**
     * Adding 'slot' as a global JSX attribute
     */
    slot?: React.ReactNode;
  }
}

declare global {
  namespace React {
    interface Attributes {
      /**
       * Ensure `slot` is available in all React components
       */
      slot?: React.ReactNode;
    }
  }
}

export {};
