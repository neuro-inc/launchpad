'use client';

import { useEffect } from 'react';

import { Instance } from '@typings';
import { toast } from '@features/toast.feature';
import { p } from '@utils';
import { request } from '@utils/helpers';

type Props = {
  appName: string;
};

export const AppWatcher: React.FC<Props> = ({ appName }) => {
  useEffect(() => {
    const run = async () => {
      try {
        const { url } = await request<Instance>(p('api/v1/apps', appName), {
          method: 'POST',
        });

        if (url) {
          window.location.replace(url);
        }
      } catch (error) {
        // @ts-expect-error todo: fix type
        toast.error(error?.message);
      }
    };

    const intervalId = setInterval(run, 5000);

    run();

    return () => {
      clearInterval(intervalId);
    };
  }, [appName]);

  return null;
};
