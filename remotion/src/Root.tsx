import React from 'react';
import {Composition} from 'remotion';
import {MontageAd, calculateMontageMetadata, montageSchema} from './MontageAd';
import {FPS, HEIGHT, WIDTH} from './constants';

export const RemotionRoot: React.FC = () => {
	return (
		<Composition
			id="MontageAd"
			component={MontageAd}
			durationInFrames={30 * FPS}
			fps={FPS}
			width={WIDTH}
			height={HEIGHT}
			schema={montageSchema}
			defaultProps={{
				title: 'Your Product Name',
				features: ['First key feature', 'Second key feature', 'Third key feature'],
				cta: 'Shop Now',
				link: 'rizzova.com',
				images: [],
				music: '',
				logoPath: '',
			}}
			calculateMetadata={calculateMontageMetadata}
		/>
	);
};
