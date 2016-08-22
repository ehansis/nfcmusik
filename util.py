import subprocess


def set_volume(percentage):
    """
    Set volume of audio output

    :param percentage: audio percentage (0-100), integer
    """

    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be in the range 0-100, got " + str(percentage))

    # set the volume via amixer
    subprocess.call(["amixer", "-M", "set", "--", "PCM", str(percentage) + "%"])

