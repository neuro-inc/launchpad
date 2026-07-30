'use client';

import { useCallback, useEffect, useState } from 'react';

import { App, WithPagination } from '@typings';
import { formatToCamelCase } from '@utils/formatters';
import { request, sortByPosition } from '@utils/helpers';

import { AppItem } from '@components/Apps/AppItem';
import { Button } from '@components/Shared';
import { Layout } from '@components/Ui';

type Props = {
  tileStyle?: React.CSSProperties;
};

const AppsLoading: React.FC<{ tileStyle?: React.CSSProperties }> = ({
  tileStyle,
}) => {
  return Array.from({ length: 3 }, (_, index) => (
    <div
      // eslint-disable-next-line react/no-array-index-key
      key={index}
      className="launchpad-app-card launchpad-app-card--loading min-h-[240px] animate-pulse rounded-xl p-6"
      data-state="loading"
      style={tileStyle}
    >
      <div className="flex gap-3">
        <div className="size-12 rounded-lg bg-neural-02" />
        <div className="flex flex-1 flex-col justify-center gap-2">
          <div className="h-5 w-2/3 rounded bg-neural-02" />
          <div className="h-4 w-1/2 rounded bg-neural-02" />
        </div>
      </div>
      <div className="mt-8 h-4 w-full rounded bg-neural-02" />
      <div className="mt-3 h-4 w-4/5 rounded bg-neural-02" />
      <div className="mt-10 flex gap-3">
        <div className="h-10 flex-1 rounded bg-neural-02" />
        <div className="h-10 flex-1 rounded bg-neural-02" />
      </div>
    </div>
  ));
};

export const AppsListClient: React.FC<Props> = ({ tileStyle }) => {
  const [apps, setApps] = useState<App[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadApps = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const { items } = await request<WithPagination<App>>('/api/v1/apps');
      const nextApps = formatToCamelCase(items) as App[];
      setApps(sortByPosition(nextApps));
    } catch (err) {
      setApps([]);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadApps();
  }, [loadApps]);

  return (
    <Layout.Container
      id="launchpad-apps-page"
      className="launchpad-apps-page launchpad-app-grid grid grid-cols-3 gap-6 pb-10 sm:grid-cols-1 md:grid-cols-2 hd:gap-4"
      data-page="apps"
    >
      {isLoading && <AppsLoading tileStyle={tileStyle} />}

      {!isLoading &&
        apps.map((app) => (
          <AppItem key={app.title} app={app} tileStyle={tileStyle} />
        ))}

      {!isLoading && error && (
        <div
          className="launchpad-app-card launchpad-app-grid__error col-span-full flex min-h-[240px] flex-col items-center justify-center gap-4 rounded-xl p-6 text-center"
          data-state="error"
          style={tileStyle}
        >
          <p className="text-h5 text-black">Applications did not load</p>
          <p className="max-w-md text-neural-04">{error}</p>
          <Button
            className="launchpad-app-grid__retry h-10 px-8"
            data-action="retry"
            onClick={loadApps}
          >
            Retry
          </Button>
        </div>
      )}

      {!isLoading && !error && apps.length === 0 && (
        <div
          className="launchpad-app-card launchpad-app-grid__empty col-span-full flex min-h-[240px] items-center justify-center rounded-xl p-6 text-center text-neural-04"
          data-state="empty"
          style={tileStyle}
        >
          No applications available.
        </div>
      )}
    </Layout.Container>
  );
};
