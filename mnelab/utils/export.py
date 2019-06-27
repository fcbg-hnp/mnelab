
def export_sef(path, raw):
    """Export a raw mne file to a sef file."""
    import struct
    import numpy as np
    import mne

    n_channels = len(raw.info['ch_names'])
    num_freq_frames = raw.n_times
    sfreq = raw.info['sfreq']
    num_aux_electrodes = n_channels - len(mne.pick_types(info, meg=False, eeg=True, exclude=[""]))
    f = open(path, 'wb')
    f.write("SE01".encode('utf-8'))
    f.write(struct.pack('I', n_channels))
    f.write(struct.pack('I', num_aux_electrodes))
    f.write(struct.pack('I', num_freq_frames))
    f.write(struct.pack('f', sfreq))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))
    f.write(struct.pack('H', 0))

    ch_names = info["ch_names"]
    for k in range(n_channels):
        ch_name = ch_names[k]
        ch_name = ch_name.ljust(8)
        f.write(ch_name.encode('utf-8'))
        print(ch_name)

    data = raw.get_data().astype(np.float32)
    data = np.reshape(data, n_channels * num_freq_frames, order='F')
    data.tofile(f)
    f.close()
