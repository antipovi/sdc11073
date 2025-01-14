import time
import uuid
from sdc11073.xml_types import pm_types
from sdc11073.xml_types import pm_qnames as pm
from sdc11073.wsdiscovery import WSDiscoverySingleAdapter
from sdc11073.definitions_sdc import SDC_v1_Definitions
from sdc11073.sdcclient import SdcClient
from sdc11073.mdib import ClientMdibContainer
from sdc11073 import observableproperties
# This example shows how to implement a very simple SDC Consumer (client)
# It will scan for SDC Providers and connect to on well known UUID

# The provider we connect to is known by its UUID
# The UUID is created from a base
baseUUID = uuid.UUID('{cc013678-79f6-403c-998f-3cc0cc050230}')
device_A_UUID = uuid.uuid5(baseUUID, "12345")

# callback function that will be called upon metric updates from the provider
def onMetricUpdate(metricsByHandle):
    # we get all changed handles as parameter, iterate over them and output
    for oneHandle in metricsByHandle:
        print("Got update on: {}".format(oneHandle))

def setEnsembleContext(theMDIB, theClient):
    # calling operation on remote device 
    print("Trying to set ensemble context of device A")
    # first we get the container to the element in the MDIB
    descriptorContainer = theMDIB.descriptions.NODETYPE.getOne(pm.EnsembleContextDescriptor)
    # get the context of our provider(client)
    contextClient = theClient.ContextService_client
    # start with empty operation handle and try to find the one we need
    operationHandle = None
    # iterate over all matching handles (can be 0..n)
    for oneOp in theMDIB.descriptions.NODETYPE.get(pm.SetContextStateOperationDescriptor, []):
        if oneOp.OperationTarget == descriptorContainer.handle:
            operationHandle = oneOp.Handle
    # now we should have a operatoin handle to work with
    # create a new ensemble context as parameter to this operation
    newEnsembleContext = contextClient.mkProposedContextObject(descriptorContainer.handle)
    newEnsembleContext.ContextAssociation = 'Assoc'
    newEnsembleContext.Identification = [
        pm_types.InstanceIdentifier(root="1.2.3", extension_string="SupervisorSuperEnsemble")]
    # execute the remote operation (based on handle) with the newly created ensemble as parameter
    contextClient.setContextState(operationHandle, [newEnsembleContext])


# main entry, will start to scan for the known provider and connect
# runs forever and consumes metrics everafter
if __name__ == '__main__':
    # start with discovery (MDPWS) that is running on the named adapter "Ethernet" (replace as you need it on your machine, e.g. "enet0" or "Ethernet)
    myDiscovery = WSDiscoverySingleAdapter("Ethernet")
    # start the discovery
    myDiscovery.start()
    # we want to search until we found one device with this client
    foundDevice = False
    # loop until we found our provider
    while not foundDevice:
        # we now search explicitly for MedicalDevices on the network
        # this will send a probe to the network and wait for responses
        # See MDPWS discovery mechanisms for details
        services = myDiscovery.search_services(types=SDC_v1_Definitions.MedicalDeviceTypesFilter)

        # now iterate through the discovered services to check if we foundDevice
        # the specific provider we search for
        for oneService in services:
            try:
                print("Got service: {}".format(oneService.getEPR()))
                # the EndPointReference is created based on the UUID of the Provider
                if oneService.getEPR() == device_A_UUID.urn:
                    print("Got a match: {}".format(oneService))
                    # now create a new SDCClient (=Consumer) that can be used
                    # for all interactions with the communication partner
                    my_client = SdcClient.from_wsd_service(oneService)
                    # start all services on the client to make sure we get updates
                    my_client.startAll()
                    # all data interactions happen through the MDIB (MedicalDeviceInformationBase)
                    # that contains data as described in the BICEPS standard
                    # this variable will contain the data from the provider
                    my_mdib = ClientMdibContainer(my_client)
                    my_mdib.init_mdib()
                    # we can subscribe to updates in the MDIB through the 
                    # Observable Properties in order to get a callback on
                    # specific changes in the MDIB
                    observableproperties.bind(my_mdib, metricsByHandle=onMetricUpdate)
                    # in order to end the 'scan' loop 
                    foundDevice = True

                    # now we demonstrate how to call a remote operation on the consumer
                    setEnsembleContext(my_mdib, my_client)
            except:
                print("Problem in discovery, ignoring it")


    # endless loop to keep the client running and get notified on metric changes through callback
    while True:
        time.sleep(1)
