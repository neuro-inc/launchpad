import { faArrowRight } from '@fortawesome/pro-regular-svg-icons';

import { App } from '@typings';
import { cn } from '@utils';

import { AppModal } from '@components/Modals/AppModal';
import { Button, Icon, Image, Link, Modal, Render } from '@components/Shared';
import { Logo } from '@components/Ui/Logo';

import { AppTags } from './AppTags';

type Props = {
  app: App;
};

export const AppItem: React.FC<Props> = ({
  app: { title, shortDescription, logo, tags },
  app,
}) => {
  return (
    <div className="peer relative z-20 flex min-h-[240px] max-w-full flex-1 flex-col gap-4 overflow-hidden rounded-xl border border-transparent bg-white p-6 transition-colors hover:border-neural-02">
      <div className="relative flex min-w-0 gap-3">
        <div className="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neural-02 bg-white">
          <Render if={logo}>
            <Image src={logo} alt="Logo" />
          </Render>
          <Render if={!logo}>
            <Logo.Icon />
          </Render>
        </div>

        <div
          className={cn('flex basis-full flex-col justify-center gap-1', {
            'justify-between': !!shortDescription,
          })}
        >
          <div className="flex items-start justify-between gap-4">
            <p className="text-h5 leading-[32px] text-black transition-colors">
              {title}
            </p>
          </div>

          <Render if={shortDescription}>
            <p className="-translate-y-1 text-neural-04">{shortDescription}</p>
          </Render>
        </div>
      </div>

      <Render if={tags}>
        <AppTags tags={tags} />
      </Render>

      <div className="mt-auto flex gap-3">
        <Modal content={<AppModal app={app} />}>
          <Button className="h-10 flex-1 capitalize" variant="secondary">
            Explore
            <Icon size="lg" icon={faArrowRight} />
          </Button>
        </Modal>

        <Link className="h-10 flex-1 capitalize" href="/">
          Install
        </Link>
      </div>
    </div>
  );
};
