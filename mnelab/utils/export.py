
def export_sef(path, raw):
    """Export a raw mne file to a sef file."""

    import numpy as np
    import struct

    n_channels = len(raw.info['ch_names'])
    num_freq_frames = raw.n_times
    sfreq = raw.info['sfreq']

    f = open(path, 'wb')
    for car in 'SE01':
        f.write(struct.pack('c', bytes(car, 'utf-8')))
    f.write(struct.pack('I', n_channels))
    f.write(struct.pack('I', 0))
    f.write(struct.pack('I', num_freq_frames))
    f.write(struct.pack('f', sfreq))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))

    for name in raw.info['ch_names']:
        n = 0
        for car in name:
            f.write(struct.pack('c', bytes(car, 'utf-8')))
            n += 1
        while n < 8:
            f.write(struct.pack('x'))
            n += 1

    data = raw.get_data().astype(np.float32)
    data = np.reshape(data, n_channels * num_freq_frames, order='F')
    data.tofile(f)
    f.close()
