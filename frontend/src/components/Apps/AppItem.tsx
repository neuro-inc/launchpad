import { faArrowRight } from '@fortawesome/pro-regular-svg-icons';

import { App } from '@typings';
import { cn, path } from '@utils';

import { AppModal } from '@components/Modals/AppModal';
import { Button, Icon, Image, Link, Modal, Render } from '@components/Shared';
import { Logo } from '@components/Ui/Logo';

import { AppTags } from './AppTags';

type Props = {
  app: App;
  tileStyle?: React.CSSProperties;
};

export const AppItem: React.FC<Props> = ({
  app: { title, descriptionShort, logo, tags, launchpadAppName },
  app,
  tileStyle,
}) => {
  return (
    <div
      className="launchpad-app-card peer relative z-20 flex min-h-[240px] max-w-full flex-1 flex-col gap-4 overflow-hidden rounded-xl border border-transparent p-6 transition-colors hover:border-neural-02"
      data-app-name={launchpadAppName}
      style={tileStyle}
    >
      <div className="launchpad-app-card__header relative flex min-w-0 gap-3">
        <div className="launchpad-app-card__logo-wrapper flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neural-02 bg-white">
          <Render if={logo}>
            <Image
              transition
              src={logo}
              width={48}
              height={48}
              alt="Logo"
              className="launchpad-app-card__logo"
            />
          </Render>
          <Render if={!logo}>
            <Logo.Icon className="launchpad-app-card__logo-fallback" />
          </Render>
        </div>

        <div
          className={cn(
            'launchpad-app-card__details flex basis-full flex-col justify-center gap-1',
            {
              'justify-between': !!descriptionShort,
            },
          )}
        >
          <div className="launchpad-app-card__heading flex items-start justify-between gap-4">
            <p className="launchpad-app-card__title text-h5 leading-[32px] text-black transition-colors">
              {title}
            </p>
          </div>

          <Render if={descriptionShort}>
            <p className="launchpad-app-card__description -translate-y-1 text-neural-04">
              {descriptionShort}
            </p>
          </Render>
        </div>
      </div>

      <Render if={tags}>
        <AppTags tags={tags} />
      </Render>

      <div className="launchpad-app-card__actions mt-auto flex gap-3">
        <Modal content={<AppModal app={app} />}>
          <Button
            className="launchpad-app-card__explore h-10 flex-1 capitalize"
            variant="secondary"
            data-action="explore"
          >
            Explore
            <Icon size="lg" icon={faArrowRight} />
          </Button>
        </Modal>

        <Link
          blank
          external
          className="launchpad-app-card__open h-10 flex-1 capitalize"
          data-action="open"
          href={path.app(launchpadAppName)}
        >
          Open
        </Link>
      </div>
    </div>
  );
};
