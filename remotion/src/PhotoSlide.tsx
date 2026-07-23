import React from 'react';
import {AbsoluteFill, Img} from 'remotion';

// Mirrors the Python resize_contain_blurred approach: the whole photo stays
// fully visible (object-fit: contain) centered over a blurred, dimmed copy
// of itself that fills the frame, so there are no dead bars and nothing
// gets cropped out.
export const PhotoSlide: React.FC<{src: string}> = ({src}) => {
	return (
		<AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
			<Img
				src={src}
				style={{
					position: 'absolute',
					inset: 0,
					width: '100%',
					height: '100%',
					objectFit: 'cover',
					filter: 'blur(45px) brightness(0.5)',
					transform: 'scale(1.15)',
				}}
			/>
			<Img
				src={src}
				style={{
					position: 'absolute',
					inset: 0,
					width: '100%',
					height: '100%',
					objectFit: 'contain',
				}}
			/>
		</AbsoluteFill>
	);
};
