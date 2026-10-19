import { Primitive } from '@typings';
import { PATH } from '@constants';
import { as, isNumber, isObject, isString } from '@utils';

type Options = Partial<{
  prefix: string;
  postfix: string;
}>;

const getDefaultPrefix = (isFirstPathUri: boolean): string =>
  isFirstPathUri ? '' : '/';

/**
 * Concatinates path elements into single string
 *
 * @example
 * p("/home"); // "/home"
 * @example
 * p("page", 1); // "/page/1"
 * @example
 * p("teams", null, "dedicated", { prefix: "" }); // "teams/dedicated"
 * @example
 * p("https://example.com", "home"); // "https://example.com/home"
 */
export const p = (...args: Array<Primitive | Options>): string => {
  const lastArgument = args.slice(-1)[0];
  const options = isObject(lastArgument) ? lastArgument : undefined;
  const paths = (options ? args.slice(0, -1) : args) as Primitive[];
  const firstPath = paths[0];
  const isFirstPathUri = isString(firstPath) && /:\//.test(firstPath);
  const { prefix = getDefaultPrefix(isFirstPathUri), postfix = '' } =
    as.o<Options>(options);

  const path =
    paths
      .map((path) => {
        if (isNumber(path)) {
          return path.toString();
        }

        if (isString(path)) {
          /**
           * Removes all "/" at the beginning
           */
          return path.replace(/^\/+/, '');
        }

        return null;
      })
      .filter(Boolean)
      .join('/') ?? '';
  const concatinatedPath = prefix + path + postfix;

  return concatinatedPath;
};

export const path = {
  app: (appName: string) => p(PATH.APPS, appName),
};
