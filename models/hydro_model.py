# -------------------------------------------------------------------------------------!
import datetime as dt
import logging
import os

import numpy as np
import pandas as pd
import xarray as xr
from utils import append_angle, pandas_to_xarray, reset_direction

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------------------!
class HydroModel(object):
    def __init__(
        self,
        parse_waves: str = None,
        parse_raos: str = None,
        parse_limits: str = None,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        # Try to import wave dataset.
        if isinstance(parse_waves, str) and os.path.isfile(parse_waves):
            try:
                self.waves_dataframe = self.parse_wave_data(file=parse_waves)
            except Exception as e:
                logger.debug(msg="Import of wave data went wrong.", exc_info=e)
                self.waves_dataframe = None

        # Try to import structure RAOs.
        if isinstance(parse_raos, str) and os.path.isfile(parse_raos):
            try:
                self.RAOs = self.parse_rao(file=parse_raos)
            except Exception as e:
                logger.debug(msg="Import of RAOs went wrong.", exc_info=e)
                self.RAOs = None

        # Try to combine both datasets.
        if (
            hasattr(self, "RAOs")
            and isinstance(self.RAOs, (pd.DataFrame, xr.DataArray))
            and isinstance(self.waves_dataframe, (pd.DataFrame, xr.DataArray))
        ):
            try:
                self.data = self.build_dataset()
            except Exception as e:
                logger.debug(
                    msg="Combining of RAOs and wave data went wrong", exc_info=e
                )

        # Set motion limits for MPI Adventure lifting operations.
        self.response_limits = pd.DataFrame(
            dict(
                type=["accelerations", "displacements"],
                surge=[0.1378, np.inf],
                sway=[0.2063, np.inf],
                heave=[0.5115, 1],
                roll=[np.degrees(0.005), 0.50],
                pitch=[np.degrees(0.01), 0.20],
                yaw=[np.degrees(0.0039), np.inf],
            )
        )

        # Derive Hs/Tp limits from excel file.
        if isinstance(parse_limits, str) and os.path.isfile(parse_limits):
            try:
                self.sea_state_limits = self.parse_limits(file=parse_limits)
            except Exception as e:
                logger.debug(msg="Import of limits from excel went wrong.", exc_info=e)
                self.sea_state_limits = None
        elif isinstance(parse_limits, str) and not os.path.isfile(parse_limits):
            raise FileNotFoundError("Could not find limit file.")

    def build_dataset(self, *args, **kwargs):
        """Combine wave and RAO data in a xarray.Dataset."""
        # Make sure not to recreate the dataset.
        if hasattr(self, "data"):
            return self.data

        # Create a dataset.
        ds = xr.Dataset(
            data_vars=dict(
                launch_rao=(["DOF", "freq", "dir"], self.RAOs),
                wave_data=(["time", "wave_parameter"], self.waves_dataframe),
            ),
            coords=dict(
                DOF=self.RAOs["DOF"],
                freq=self.RAOs["freq"],
                dir=self.RAOs["dir"],
                time=self.waves_dataframe.index.values,
                wave_parameter=self.waves_dataframe.columns,
            ),
        )

        # Return the result.
        return ds

    def parse_limits(self, file, *args, **kwargs):
        """Read contents of wave limit excel file."""
        # Import and process limits from excel file.
        df = pd.read_excel(file, index_col=[0])
        df.index.names = ["dir"]
        df.columns.names = ["freq"]
        df = xr.DataArray(df)

        # Copy 0-degree row to 360-degree row.
        df = xr.concat(
            # Max. sign. wave height is zero after Tp=12.00 [s].
            [df, xr.DataArray(np.zeros(24), dims="dir", coords=dict(freq=12))],
            dim="freq",
        )

        # Return limit DataArray.
        return df

    def parse_rao(self, file, *args, **kwargs):
        """Read the contents of a response amplitude operator file."""
        # Make sure not to reload the data.
        if hasattr(self, "RAO"):
            return self.RAO

        # Read using pandas and store in a xarray.DataArray
        df = (
            pd.read_csv(file)  # Read .csv.
            .pipe(reset_direction)  # reset wave angle range.
            .set_index(["RAOPeriodOrFreq", "dir"])  # Create multi-index.
            .unstack()  # Turn multi-index in a 3D kind of dataframe.
            .pipe(pandas_to_xarray)  # Convert to a xarray.DataArray
            .pipe(append_angle)  # Copies the 0[deg] RAO to 360[deg].
        )

        # Return the result
        return df

    def parse_wave_data(self, file, *args, **kwargs):
        """Read the contents of a DHI wave data file."""
        # Make sure not to reload the data.
        if hasattr(self, "wave"):
            return self.wave

        # Import wave data.
        df = pd.read_csv(
            file,
            skiprows=[0],
            parse_dates={"datetime": ["YYYY", "M", "D", "HH", "MM", "SS"]},
            date_parser=lambda x: dt.datetime.strptime(x, "%Y %m %d %H %M %S"),
        ).set_index("datetime")

        # Return the result.
        return df

    def sea_state_limit_expression(self, Hm0, Tp):
        # Query the maximum wave height.
        max_wave_height = self.sea_state_limits.interp(
            # Note, ship is aligned with waves.
            dict(dir=180, freq=xr.DataArray(Tp, dims="time"))
        )

        return Hm0 >= max_wave_height

    def RAO_limit_expression(
        self, RAOSurgeAmp, RAOSwayAmp, RAOHeaveAmp, RAORollAmp, RAOPitchAmp, RAOYawAmp
    ):

        try:
            limits = self.response_limits.loc[self.response_limits["type"] == self.type]
        except Exception as e:
            logger.debug(msg="`self.type` not defined.", exc_info=e)
            limits = self.response_limits.loc[
                self.response_limits["type"] == "accelerations"
            ]

        return (
            (RAOSurgeAmp >= float(limits["surge"]))
            | (RAOSwayAmp >= float(limits["sway"]))
            | (RAOHeaveAmp >= float(limits["heave"]))
            | (RAORollAmp >= float(limits["roll"]))
            | (RAOPitchAmp >= float(limits["pitch"]))
            | (RAOYawAmp >= float(limits["yaw"]))
        )

    def response_motions(
        self, method: str = "mean-wave-dir", type="displacements", *args, **kwargs
    ):
        """Compute the response motions.

        Compute the response motions of the structure based on the
        provided wave dataset. The method argument allows to define how
        to compute the response motions with respect to the wave angle.
        `method="smallest"` computes the most favourable angle of attack
        by running an optimiser step. `method="mean-wave-dir"` computes
        the response motions corresponding to vessel aimed at the mean
        wave direction.

        """
        # -----------------------------------------------------------------------------!
        assert type in [
            "accelerations",
            "displacements",
        ], "`type` accepts only `'displacements'` or `'accelerations'`"

        self.type = type

        # -----------------------------------------------------------------------------!
        if method == "mean-wave-dir":

            # Determine the incoming wave angle.
            wave_angle_windsea = (
                180
                + self.data["wave_data"].sel(dict(wave_parameter="MWDWS"))
                - self.data["wave_data"].sel(dict(wave_parameter="MWD"))
            ) % 360

            wave_angle_swell = (
                180
                + self.data["wave_data"].sel(dict(wave_parameter="MWDS"))
                - self.data["wave_data"].sel(dict(wave_parameter="MWD"))
            ) % 360

            # compute windsea component response.
            windsea_rao = self.data["launch_rao"].interp(
                dict(
                    freq=self.data["wave_data"].sel(dict(wave_parameter="TpWS")),
                    dir=wave_angle_windsea,
                ),
                kwargs=dict(fill_value=0),
            )

            windsea_response = (
                windsea_rao
                * self.data["wave_data"].sel(dict(wave_parameter="Hm0WS"))
                / 2
            )

            # compute swell component response.
            swell_rao = self.data["launch_rao"].interp(
                dict(
                    freq=self.data["wave_data"].sel(dict(wave_parameter="TpS")),
                    dir=wave_angle_swell,
                ),
                kwargs=dict(fill_value=0),
            )

            swell_response = (
                swell_rao * self.data["wave_data"].sel(dict(wave_parameter="Hm0S")) / 2
            )

            # find the coupled displacements.
            if type == "displacements":
                # compute coupled response.
                coupled_response = windsea_response + swell_response

            # find the coupled accelerations.
            elif type == "accelerations":

                # compute the accelerations.
                windsea_response = (
                    windsea_response
                    * (
                        2
                        * np.pi
                        / self.data["wave_data"].sel(dict(wave_parameter="TpWS"))
                    )
                    ** 2
                )

                swell_response = (
                    swell_response
                    * (
                        2
                        * np.pi
                        / self.data["wave_data"].sel(dict(wave_parameter="TpS"))
                    )
                    ** 2
                )

                # compute coupled response.
                coupled_response = windsea_response + swell_response

            # Convert to pandas.DataFrame.
            coupled_response = pd.DataFrame(
                data=coupled_response.values.T,
                columns=coupled_response["DOF"].values,
                index=coupled_response["time"].values,
            ).rename_axis("datetime")

            # return dataframe.
            return coupled_response

        # -----------------------------------------------------------------------------!
        elif method == "smallest":

            # possible vessel headings.
            vessel_heading = xr.DataArray(
                np.arange(0, 360, 45),
                dims="dir",
                coords=dict(dir=np.arange(0, 360, 45)),
            )

            # determine the incoming wave angles.
            windsea_dir = self.data["wave_data"].sel(dict(wave_parameter="MWDWS"))
            wave_angle_windsea = (180 - windsea_dir + vessel_heading) % 360

            swell_dir = self.data["wave_data"].sel(dict(wave_parameter="MWDWS"))
            wave_angle_swell = (180 - swell_dir + vessel_heading) % 360

            # compute windsea component.
            windsea_rao = self.data["launch_rao"].interp(
                dict(
                    freq=self.data["wave_data"].sel(dict(wave_parameter="TpWS")),
                    dir=wave_angle_windsea,
                ),
                kwargs=dict(fill_value=0),
            )

            windsea_response = (
                windsea_rao
                * self.data["wave_data"].sel(dict(wave_parameter="Hm0WS"))
                / 2
            )

            # compute swell component.
            swell_rao = self.data["launch_rao"].interp(
                dict(
                    freq=self.data["wave_data"].sel(dict(wave_parameter="TpWS")),
                    dir=wave_angle_swell,
                ),
                kwargs=dict(fill_value=0),
            )

            swell_response = (
                swell_rao * self.data["wave_data"].sel(dict(wave_parameter="Hm0S")) / 2
            )

            # find the coupled displacements.
            if type == "displacements":
                # compute coupled response.
                coupled_response = windsea_response + swell_response

            # find the coupled accelerations.
            elif type == "accelerations":

                # compute the accelerations.
                windsea_response = (
                    windsea_response
                    * (
                        2
                        * np.pi
                        / self.data["wave_data"].sel(dict(wave_parameter="TpWS"))
                    )
                    ** 2
                )

                swell_response = (
                    swell_response
                    * (
                        2
                        * np.pi
                        / self.data["wave_data"].sel(dict(wave_parameter="TpS"))
                    )
                    ** 2
                )

                # compute coupled response.
                coupled_response = windsea_response + swell_response

            # compute the most favourable orientation angle.
            best_angle = (
                coupled_response.loc[["RAOSurgeAmp", "RAOSwayAmp", "RAOHeaveAmp"]]
                .to_dataframe("launch_rao")
                .reset_index()
                .groupby(["time", "dir"])["launch_rao"]
                .sum()
                .unstack()
                .idxmin(axis=1)
                .to_xarray()
            )

            # return the optimised response motions.
            coupled_response = coupled_response.sel(dict(dir=best_angle))

            # Convert to pandas.DataFrame.
            coupled_response = pd.DataFrame(
                data=coupled_response.values.T,
                columns=coupled_response["DOF"].values,
                index=coupled_response["time"].values,
            ).rename_axis("datetime")

            # return dataframe.
            return coupled_response

        # -----------------------------------------------------------------------------!
        else:
            raise ValueError("Method excepts only `mean-wave-dir` or `smallest`.")
