export type KeysOf<Target extends object> = keyof Target;

export type ValuesOf<Target extends object> = Target[keyof Target];
