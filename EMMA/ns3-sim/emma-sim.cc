#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/lte-module.h"
#include "ns3/applications-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/config-store-module.h"
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("EMMASim");

class EMMASimulator
{
public:
    EMMASimulator()
    {
        // Create LTE helper
        m_lteHelper = CreateObject<LteHelper>();
        
        // Create EPC helper
        m_epcHelper = CreateObject<PointToPointEpcHelper>();
        m_lteHelper->SetEpcHelper(m_epcHelper);
        
        // Create PGW node
        m_pgw = m_epcHelper->GetPgwNode();
        
        // Create remote host
        m_remoteHost = CreateObject<Node>();
        InternetStackHelper internet;
        internet.Install(m_remoteHost);
        
        // Create the Internet
        PointToPointHelper p2ph;
        p2ph.SetDeviceAttribute("DataRate", DataRateValue(DataRate("100Gb/s")));
        p2ph.SetChannelAttribute("Delay", TimeValue(MilliSeconds(10)));
        NetDeviceContainer internetDevices = p2ph.Install(m_pgw, m_remoteHost);
        
        // Assign IP addresses
        Ipv4AddressHelper ipv4h;
        ipv4h.SetBase("1.0.0.0", "255.0.0.0");
        Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign(internetDevices);
        
        // Create eNodeB
        m_enbNodes.Create(1);
        m_ueNodes.Create(10);
        
        // Install mobility model
        MobilityHelper mobility;
        mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mobility.Install(m_enbNodes);
        mobility.Install(m_ueNodes);
        
        // Install LTE devices
        NetDeviceContainer enbDevs = m_lteHelper->InstallEnbDevice(m_enbNodes);
        NetDeviceContainer ueDevs = m_lteHelper->InstallUeDevice(m_ueNodes);
        
        // Install IP stack on UEs
        internet.Install(m_ueNodes);
        Ipv4InterfaceContainer ueIpIface = m_epcHelper->AssignUeIpv4Address(ueDevs);
        
        // Attach UEs to eNodeB
        m_lteHelper->Attach(ueDevs, enbDevs.Get(0));
        
        // Enable traces
        m_lteHelper->EnableTraces();
    }
    
    void ConfigureMulticast()
    {
        // Create multicast group
        Ipv4Address multicastGroup("239.255.0.1");
        uint16_t port = 5000;
        
        // Create multicast source application
        UdpEchoClientHelper echoClient(multicastGroup, port);
        echoClient.SetAttribute("MaxPackets", UintegerValue(1));
        echoClient.SetAttribute("Interval", TimeValue(Seconds(1.0)));
        echoClient.SetAttribute("PacketSize", UintegerValue(1024));
        
        ApplicationContainer clientApps = echoClient.Install(m_remoteHost);
        clientApps.Start(Seconds(1.0));
        clientApps.Stop(Seconds(10.0));
        
        // Create multicast sink applications on UEs
        for (uint32_t i = 0; i < m_ueNodes.GetN(); ++i)
        {
            UdpEchoServerHelper echoServer(port);
            ApplicationContainer serverApps = echoServer.Install(m_ueNodes.Get(i));
            serverApps.Start(Seconds(0.0));
            serverApps.Stop(Seconds(11.0));
        }
    }
    
    void Run(Time duration)
    {
        Simulator::Stop(duration);
        Simulator::Run();
        Simulator::Destroy();
    }
    
private:
    Ptr<LteHelper> m_lteHelper;
    Ptr<PointToPointEpcHelper> m_epcHelper;
    NodeContainer m_enbNodes;
    NodeContainer m_ueNodes;
    Ptr<Node> m_pgw;
    Ptr<Node> m_remoteHost;
};

int main(int argc, char *argv[])
{
    LogComponentEnable("EMMASim", LOG_LEVEL_INFO);
    
    CommandLine cmd(__FILE__);
    cmd.Parse(argc, argv);
    
    EMMASimulator simulator;
    simulator.ConfigureMulticast();
    simulator.Run(Seconds(11.0));
    
    return 0;
} 