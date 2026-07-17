import { faLink } from '@fortawesome/pro-light-svg-icons';

import { App } from '@typings';
import { path } from '@utils/path';

import { AppItemLink } from '@components/Apps/AppItemLink';
import { Image, Link, Render } from '@components/Shared';
import { Logo } from '@components/Ui/Logo';

type Props = {
  app: App;
};

export const AppModal: React.FC<Props> = ({
  app: {
    logo,
    title,
    descriptionShort,
    descriptionLong,
    documentationUrls,
    externalUrls,
    launchpadAppName,
  },
}) => {
  const makeDocumentationLink = ({
    text,
    url,
  }: App['documentationUrls'][number]) => (
    <AppItemLink
      external
      key={url}
      to={url}
      title={text}
      className="launchpad-app-modal__link"
    />
  );

  const makeReferenceLink = ({ text, url }: App['externalUrls'][number]) => (
    <AppItemLink
      icon={faLink}
      key={url}
      to={url}
      title={text}
      className="launchpad-app-modal__link"
    />
  );

  return (
    <div
      className="launchpad-app-modal relative flex w-[800px] max-w-full flex-col gap-8 overflow-auto rounded-2xl bg-white p-14 sm:px-4 md:px-8"
      data-app-name={launchpadAppName}
      data-modal="app-details"
    >
      <div className="launchpad-app-modal__hero relative flex min-w-0 gap-9 sm:gap-5">
        <div className="launchpad-app-modal__logo-wrapper flex size-[160px] shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neural-02 bg-white sm:size-20">
          <Render if={logo}>
            <Image
              transition
              src={logo}
              width={160}
              height={160}
              alt="Logo"
              className="launchpad-app-modal__logo"
            />
          </Render>
          <Render if={!logo}>
            <Logo.Icon className="launchpad-app-modal__logo-fallback size-28" />
          </Render>
        </div>

        <div className="launchpad-app-modal__info flex basis-full flex-col gap-3">
          <p className="launchpad-app-modal__title text-h4">{title}</p>
          <Render if={descriptionShort}>
            <p className="launchpad-app-modal__short-description text-neural-04 sm:-mt-2">
              {descriptionShort}
            </p>
          </Render>
          <div className="launchpad-app-modal__actions mt-auto flex justify-end">
            <Link
              blank
              external
              className="launchpad-app-modal__open px-10 sm:w-full"
              data-action="open"
              href={path.app(launchpadAppName)}
            >
              Open
            </Link>
          </div>
        </div>
      </div>
      <Render if={descriptionLong}>
        <p className="launchpad-app-modal__long-description text-neural-04">
          {descriptionLong}
        </p>
      </Render>
      <Render if={documentationUrls}>
        <div
          className="launchpad-app-modal__section flex flex-col gap-3"
          data-section="documentation"
        >
          <p className="launchpad-app-modal__section-title text-h6">
            Documentation
          </p>
          {documentationUrls.map(makeDocumentationLink)}
        </div>
      </Render>
      <Render if={externalUrls}>
        <div
          className="launchpad-app-modal__section flex flex-col gap-3"
          data-section="references"
        >
          <p className="launchpad-app-modal__section-title text-h6">
            References
          </p>
          {externalUrls.map(makeReferenceLink)}
        </div>
      </Render>
    </div>
  );
};
