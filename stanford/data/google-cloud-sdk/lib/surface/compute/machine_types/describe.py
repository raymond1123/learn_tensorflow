# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Command for describing machine types."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute import flags as compute_flags
from googlecloudsdk.command_lib.compute.machine_types import flags


class Describe(base.DescribeCommand):
  """Describe a Google Compute Engine machine type.

  *{command}* displays all data associated with a Google Compute
  Engine machine type.
  """

  @staticmethod
  def Args(parser):
    Describe.MachineTypeArg = flags.MakeMachineTypeArg()
    Describe.MachineTypeArg.AddArgument(parser, operation_type='describe')

  def Run(self, args):
    holder = base_classes.ComputeApiHolder(self.ReleaseTrack())
    client = holder.client

    machine_type_ref = Describe.MachineTypeArg.ResolveAsResource(
        args,
        holder.resources,
        scope_lister=compute_flags.GetDefaultScopeLister(client))

    request = client.messages.ComputeMachineTypesGetRequest(
        **machine_type_ref.AsDict())

    return client.MakeRequests([(client.apitools_client.machineTypes, 'Get',
                                 request)])[0]
