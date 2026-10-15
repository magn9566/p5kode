
import cv2

from ids_peak import ids_peak
from ids_peak import ids_peak_ipl_extension
from ids_peak_ipl import ids_peak_ipl


def main():
    ids_peak.Library.Initialize()

    data_stream = None
    remote = None
    started = False

    try:
        # Find connected IDS cameras
        manager = ids_peak.DeviceManager.Instance()
        manager.Update()

        if len(manager.Devices()) == 0:
            print("No IDS camera found!")
            return

        # Open first camera
        device = manager.Devices()[0].OpenDevice(
            ids_peak.DeviceAccessType_Control
        )

        print("Camera connected!")

        remote = device.RemoteDevice().NodeMaps()[0]

        # Set continuous acquisition
        remote.FindNode("AcquisitionMode").SetCurrentEntry(
            "Continuous"
        )
        remote.FindNode("TriggerMode").SetCurrentEntry("Off")

        # Open image stream
        data_stream = device.DataStreams()[0].OpenDataStream()

        payload_size = remote.FindNode("PayloadSize").Value()
        buffer_count = data_stream.NumBuffersAnnouncedMinRequired()

        for _ in range(buffer_count):
            buffer = data_stream.AllocAndAnnounceBuffer(
                payload_size
            )
            data_stream.QueueBuffer(buffer)

        # Start acquisition
        remote.FindNode("TLParamsLocked").SetValue(1)
        data_stream.StartAcquisition()
        remote.FindNode("AcquisitionStart").Execute()
        remote.FindNode("AcquisitionStart").WaitUntilDone()
        started = True

        print("Camera running! Press Q to exit.")

        while True:
            buffer = data_stream.WaitForFinishedBuffer(5000)

            try:
                # IDS buffer -> image
                image = ids_peak_ipl_extension.BufferToImage(
                    buffer
                )

                # Convert to OpenCV BGR format
                converted = image.ConvertTo(
                    ids_peak_ipl.PixelFormatName_BGR8
                )

                frame = converted.get_numpy_3D().copy()

            finally:
                data_stream.QueueBuffer(buffer)

            # Resize preview (original frame stays full size)
            preview = cv2.resize(frame, (1000, 750))

            cv2.imshow("IDS Camera - OpenCV", preview)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        if started:
            remote.FindNode("AcquisitionStop").Execute()
            remote.FindNode("AcquisitionStop").WaitUntilDone()

            data_stream.StopAcquisition(
                ids_peak.AcquisitionStopMode_Default
            )

            data_stream.Flush(
                ids_peak.DataStreamFlushMode_DiscardAll
            )

            for buffer in data_stream.AnnouncedBuffers():
                data_stream.RevokeBuffer(buffer)

            remote.FindNode("TLParamsLocked").SetValue(0)

        cv2.destroyAllWindows()
        ids_peak.Library.Close()


if __name__ == "__main__":
    main()
